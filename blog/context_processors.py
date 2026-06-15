from .models import Category, Post
from django.db.models import Count


def blog_context(request):
    """Inject global context into every template."""
    categories = Category.objects.annotate(post_count=Count("posts")).order_by("name")
    recent_posts = Post.published.order_by("-publish")[:4]
    return {
        "global_categories": categories,
        "global_recent_posts": recent_posts,
    }
