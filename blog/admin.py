from django.contrib import admin
from django.utils.html import format_html
from .models import Post, Comment, Category, Profile, Bookmark, PostLike, Newsletter, Contact


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "post_count"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]

    def post_count(self, obj):
        return obj.posts.count()


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "category", "status", "featured", "views", "publish"]
    list_filter = ["status", "featured", "category", "publish"]
    list_editable = ["status", "featured"]
    search_fields = ["title", "body"]
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ["author"]
    date_hierarchy = "publish"
    ordering = ["-publish"]
    actions = ["make_published", "make_draft"]

    def make_published(self, request, queryset):
        queryset.update(status="published")
    make_published.short_description = "Mark selected posts as published"

    def make_draft(self, request, queryset):
        queryset.update(status="draft")
    make_draft.short_description = "Mark selected posts as draft"

    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" height="50"/>', obj.cover_image.url)
        return "-"
    cover_preview.short_description = "Cover"


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["post", "author", "name", "created", "active"]
    list_filter = ["active", "created"]
    search_fields = ["name", "email", "body"]
    list_editable = ["active"]
    actions = ["approve_comments"]

    def approve_comments(self, request, queryset):
        queryset.update(active=True)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "location", "newsletter_subscribed"]
    search_fields = ["user__username", "user__email"]


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ["email", "confirmed", "created"]
    list_filter = ["confirmed"]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "subject", "created", "read"]
    list_filter = ["read"]
    list_editable = ["read"]


admin.site.register(Bookmark)
admin.site.register(PostLike)
