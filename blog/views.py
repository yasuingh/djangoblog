from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView
from django.utils.decorators import method_decorator
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from .models import Post, Comment, Category, Bookmark, PostLike, Newsletter, Profile, Contact
from .forms import CommentForm, PostForm, ProfileForm, NewsletterForm, ContactForm, SearchForm
import json


# ── Home ────────────────────────────────────────────────────────────────────
def home(request):
    posts = Post.published.select_related("author", "category").prefetch_related("tags")
    featured = posts.filter(featured=True)[:3]
    latest = posts.exclude(featured=True)[:6]
    categories = Category.objects.annotate(post_count=Count("posts")).filter(post_count__gt=0)[:8]
    popular = posts.order_by("-views")[:5]
    context = {
        "featured_posts": featured,
        "latest_posts": latest,
        "categories": categories,
        "popular_posts": popular,
    }
    return render(request, "blog/home.html", context)


# ── Post list ────────────────────────────────────────────────────────────────
class PostListView(ListView):
    model = Post
    template_name = "blog/post_list.html"
    context_object_name = "posts"
    paginate_by = 9

    def get_queryset(self):
        return Post.published.select_related("author", "category").prefetch_related("tags")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = Category.objects.annotate(post_count=Count("posts"))
        ctx["popular_tags"] = Post.published.values("tags__name", "tags__slug").annotate(
            count=Count("id")).order_by("-count")[:15]
        return ctx


# ── Post detail ──────────────────────────────────────────────────────────────
def post_detail(request, year, month, day, slug):
    post = get_object_or_404(
        Post.published,
        slug=slug,
        publish__year=year,
        publish__month=month,
        publish__day=day,
    )
    post.increment_views()

    comments = post.comments.filter(active=True, parent=None).select_related("author__profile").prefetch_related("replies__author__profile")
    comment_form = CommentForm()

    # Like status
    is_liked = False
    is_bookmarked = False
    if request.user.is_authenticated:
        is_liked = PostLike.objects.filter(user=request.user, post=post).exists()
        is_bookmarked = Bookmark.objects.filter(user=request.user, post=post).exists()

    if request.method == "POST" and post.allow_comments:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            parent_id = request.POST.get("parent_id")
            if parent_id:
                comment.parent = get_object_or_404(Comment, id=parent_id)
            if request.user.is_authenticated:
                comment.author = request.user
            comment.save()
            messages.success(request, "Your comment has been posted.")
            return redirect(post.get_absolute_url())

    context = {
        "post": post,
        "comments": comments,
        "comment_form": comment_form,
        "related_posts": post.get_related_posts(),
        "is_liked": is_liked,
        "is_bookmarked": is_bookmarked,
        "total_likes": post.likes.count(),
    }
    return render(request, "blog/post_detail.html", context)


# ── Category ─────────────────────────────────────────────────────────────────
def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    posts = Post.published.filter(category=category).select_related("author")
    paginator = Paginator(posts, 9)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "blog/category_detail.html", {"category": category, "page_obj": page})


# ── Tag ──────────────────────────────────────────────────────────────────────
def tag_detail(request, slug):
    from taggit.models import Tag
    tag = get_object_or_404(Tag, slug=slug)
    posts = Post.published.filter(tags__in=[tag]).select_related("author")
    paginator = Paginator(posts, 9)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "blog/tag_detail.html", {"tag": tag, "page_obj": page})


# ── Author ────────────────────────────────────────────────────────────────────
def author_detail(request, username):
    author = get_object_or_404(User, username=username)
    posts = Post.published.filter(author=author).select_related("category")
    paginator = Paginator(posts, 9)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "blog/author_detail.html", {"author": author, "page_obj": page})


# ── Search ───────────────────────────────────────────────────────────────────
def search(request):
    form = SearchForm(request.GET or None)
    results = Post.objects.none()
    query = ""
    if form.is_valid():
        query = form.cleaned_data["query"]
        results = Post.published.filter(
            Q(title__icontains=query) | Q(body__icontains=query) | Q(excerpt__icontains=query)
        ).distinct()
    paginator = Paginator(results, 9)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "blog/search.html", {"form": form, "query": query, "page_obj": page})


# ── AJAX: Toggle Like ─────────────────────────────────────────────────────────
@login_required
@require_POST
def toggle_like(request):
    data = json.loads(request.body)
    post = get_object_or_404(Post, pk=data.get("post_id"))
    like, created = PostLike.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    return JsonResponse({"liked": liked, "total": post.likes.count()})


# ── AJAX: Toggle Bookmark ──────────────────────────────────────────────────
@login_required
@require_POST
def toggle_bookmark(request):
    data = json.loads(request.body)
    post = get_object_or_404(Post, pk=data.get("post_id"))
    bookmark, created = Bookmark.objects.get_or_create(user=request.user, post=post)
    if not created:
        bookmark.delete()
        bookmarked = False
    else:
        bookmarked = True
    return JsonResponse({"bookmarked": bookmarked})


# ── AJAX: Like Comment ────────────────────────────────────────────────────────
@login_required
@require_POST
def like_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if request.user in comment.likes.all():
        comment.likes.remove(request.user)
        liked = False
    else:
        comment.likes.add(request.user)
        liked = True
    return JsonResponse({"liked": liked, "total": comment.total_likes})


# ── Post CRUD ─────────────────────────────────────────────────────────────────
@login_required
def post_create(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.save_m2m()
            messages.success(request, "Post created successfully.")
            return redirect(post.get_absolute_url())
    else:
        form = PostForm()
    return render(request, "blog/post_form.html", {"form": form, "action": "Create"})


@login_required
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Post updated successfully.")
            return redirect(post.get_absolute_url())
    else:
        form = PostForm(instance=post)
    return render(request, "blog/post_form.html", {"form": form, "action": "Edit", "post": post})


@login_required
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    if request.method == "POST":
        post.delete()
        messages.success(request, "Post deleted.")
        return redirect("blog:post_list")
    return render(request, "blog/post_confirm_delete.html", {"post": post})


# ── Dashboard ─────────────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    posts = Post.objects.filter(author=request.user).order_by("-created")
    bookmarks = Bookmark.objects.filter(user=request.user).select_related("post__author")
    stats = {
        "total_posts": posts.filter(status="published").count(),
        "total_views": sum(p.views for p in posts),
        "total_comments": Comment.objects.filter(post__author=request.user).count(),
        "draft_count": posts.filter(status="draft").count(),
    }
    return render(request, "blog/dashboard.html", {"posts": posts, "bookmarks": bookmarks, "stats": stats})


# ── Profile ──────────────────────────────────────────────────────────────────
@login_required
def profile_edit(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("blog:dashboard")
    else:
        form = ProfileForm(instance=profile)
    return render(request, "blog/profile_edit.html", {"form": form})


# ── Newsletter ────────────────────────────────────────────────────────────────
def newsletter_subscribe(request):
    if request.method == "POST":
        form = NewsletterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            sub, created = Newsletter.objects.get_or_create(email=email)
            if created:
                messages.success(request, "Subscribed! Check your email to confirm.")
            else:
                messages.info(request, "You are already subscribed.")
    return redirect(request.META.get("HTTP_REFERER", "/"))


def newsletter_confirm(request, token):
    sub = get_object_or_404(Newsletter, token=token)
    sub.confirmed = True
    sub.save()
    messages.success(request, "Subscription confirmed. Thank you!")
    return redirect("blog:home")


# ── Contact ───────────────────────────────────────────────────────────────────
def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your message has been sent!")
            return redirect("blog:contact")
    else:
        form = ContactForm()
    return render(request, "blog/contact.html", {"form": form})


# ── About ─────────────────────────────────────────────────────────────────────
def about(request):
    return render(request, "blog/about.html")


# ── RSS Feed helper redirect ───────────────────────────────────────────────────
def bookmarks_list(request):
    if not request.user.is_authenticated:
        return redirect("account_login")
    bookmarks = Bookmark.objects.filter(user=request.user).select_related("post__author", "post__category")
    return render(request, "blog/bookmarks.html", {"bookmarks": bookmarks})
