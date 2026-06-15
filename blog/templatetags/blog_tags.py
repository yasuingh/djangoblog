from django import template
from django.utils.safestring import mark_safe
import markdown as md
import bleach

register = template.Library()

ALLOWED_TAGS = [
    "p", "b", "i", "strong", "em", "a", "ul", "ol", "li",
    "blockquote", "code", "pre", "h1", "h2", "h3", "h4", "h5", "h6",
    "img", "table", "thead", "tbody", "tr", "th", "td", "br", "hr",
]
ALLOWED_ATTRS = {"a": ["href", "title"], "img": ["src", "alt"]}


@register.filter(name="markdown")
def render_markdown(value):
    html = md.markdown(value, extensions=["fenced_code", "tables", "codehilite"])
    clean = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)
    return mark_safe(clean)


@register.filter
def reading_label(minutes):
    return f"{minutes} min read"


@register.simple_tag
def get_popular_posts(count=5):
    from blog.models import Post
    return Post.published.order_by("-views")[:count]


@register.inclusion_tag("blog/tags/social_share.html")
def social_share(post):
    return {"post": post}


@register.filter
def pluralize_comments(count):
    return f"{count} comment{'s' if count != 1 else ''}"
