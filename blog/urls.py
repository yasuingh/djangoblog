from django.urls import path
from . import views
from .feeds import LatestPostsFeed
from django.conf import settings
from django.conf.urls.static import static

app_name = "blog"

urlpatterns = [
    path("", views.home, name="home"),
    path("posts/", views.PostListView.as_view(), name="post_list"),
    path("posts/create/", views.post_create, name="post_create"),
    path("posts/<int:pk>/edit/", views.post_edit, name="post_edit"),
    path("posts/<int:pk>/delete/", views.post_delete, name="post_delete"),
    path("posts/<int:year>/<int:month>/<int:day>/<slug:slug>/", views.post_detail, name="post_detail"),
    path("category/<slug:slug>/", views.category_detail, name="category_detail"),
    path("tag/<slug:slug>/", views.tag_detail, name="tag_detail"),
    path("author/<str:username>/", views.author_detail, name="author_detail"),
    path("search/", views.search, name="search"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("bookmarks/", views.bookmarks_list, name="bookmarks"),
    path("contact/", views.contact, name="contact"),
    path("about/", views.about, name="about"),
    # AJAX
    path("ajax/like/", views.toggle_like, name="toggle_like"),
    path("ajax/bookmark/", views.toggle_bookmark, name="toggle_bookmark"),
    path("ajax/comment/<int:pk>/like/", views.like_comment, name="like_comment"),
    # Newsletter
    path("newsletter/subscribe/", views.newsletter_subscribe, name="newsletter_subscribe"),
    path("newsletter/confirm/<uuid:token>/", views.newsletter_confirm, name="newsletter_confirm"),
    # Feed
    path("feed/", LatestPostsFeed(), name="post_feed"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
