from django.contrib.syndication.views import Feed
from django.urls import reverse
from .models import Post


class LatestPostsFeed(Feed):
    title = "DjangoBlog - Latest Posts"
    link = "/feed/"
    description = "Latest posts from DjangoBlog."

    def items(self):
        return Post.published.order_by("-publish")[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt

    def item_pubdate(self, item):
        return item.publish

    def item_author_name(self, item):
        return item.author.get_full_name() or item.author.username
