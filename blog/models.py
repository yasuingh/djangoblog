from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone
from taggit.managers import TaggableManager
from ckeditor_uploader.fields import RichTextUploadingField
import uuid


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="categories/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:category_detail", kwargs={"slug": self.slug})


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    
    
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    website = models.URLField(blank=True)
    twitter = models.CharField(max_length=100, blank=True)
    github = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=100, blank=True)
    newsletter_subscribed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def get_absolute_url(self):
        return reverse("blog:author_detail", kwargs={"username": self.user.username})

    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return "/static/img/default-avatar.svg"


class PublishedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status="published")


class Post(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]

    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=250, unique_for_date="publish")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blog_posts")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts")
    cover_image = models.ImageField(upload_to="posts/%Y/%m/", blank=True, null=True)
    excerpt = models.TextField(max_length=300, blank=True)
    body = RichTextUploadingField()
    publish = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    featured = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0)
    reading_time = models.PositiveSmallIntegerField(default=1)  # minutes
    meta_description = models.CharField(max_length=160, blank=True)
    allow_comments = models.BooleanField(default=True)

    tags = TaggableManager(blank=True)
    objects = models.Manager()
    published = PublishedManager()

    class Meta:
        ordering = ["-publish"]
        indexes = [
            models.Index(fields=["-publish"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
       if not self.slug:
        self.slug = slugify(self.title)
    # Strip HTML before counting words
       import bleach
       if self.body:
        plain_body = bleach.clean(self.body, tags=[], strip=True)
        word_count = len(plain_body.split())
       else:
        word_count = 0
       self.reading_time = min(max(1, round(word_count / 200)), 32767)
       if not self.excerpt:
        plain = bleach.clean(self.body, tags=[], strip=True) if self.body else ""
        self.excerpt = plain[:297] + "..." if len(plain) > 300 else plain
       super().save(*args, **kwargs)
 
    def get_absolute_url(self):
        return reverse("blog:post_detail", kwargs={
            "year": self.publish.year,
            "month": self.publish.month,
            "day": self.publish.day,
            "slug": self.slug,
        })

    def get_related_posts(self, count=4):
        post_tags_ids = self.tags.values_list("id", flat=True)
        similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=self.id)
        from django.db.models import Count
        similar_posts = similar_posts.annotate(same_tags=Count("tags")).order_by("-same_tags", "-publish")
        return similar_posts[:count]

    def increment_views(self):
        Post.objects.filter(pk=self.pk).update(views=models.F("views") + 1)


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments", null=True, blank=True)
    name = models.CharField(max_length=80, blank=True)
    email = models.EmailField(blank=True)
    body = models.TextField(max_length=1000)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)
    likes = models.ManyToManyField(User, related_name="liked_comments", blank=True)

    class Meta:
        ordering = ["created"]

    def __str__(self):
        return f"Comment by {self.author or self.name} on {self.post}"

    @property
    def total_likes(self):
        return self.likes.count()

    def get_display_name(self):
        if self.author:
            return self.author.get_full_name() or self.author.username
        return self.name or "Anonymous"


class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookmarks")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="bookmarks")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "post")
        ordering = ["-created"]

    def __str__(self):
        return f"{self.user.username} bookmarked {self.post.title}"


class PostLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_likes")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "post")


class Newsletter(models.Model):
    email = models.EmailField(unique=True)
    confirmed = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return self.email


class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.subject} from {self.name}"
