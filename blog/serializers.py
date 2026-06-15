from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Post, Comment, Category, Profile


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description"]


class AuthorSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "avatar"]

    def get_avatar(self, obj):
        if hasattr(obj, "profile") and obj.profile.avatar:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.profile.avatar.url) if request else obj.profile.avatar.url
        return None


class CommentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author", "name", "body", "created", "active"]
        read_only_fields = ["active", "created"]


class PostListSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = serializers.StringRelatedField(many=True)
    url = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id", "title", "slug", "author", "category", "tags",
            "excerpt", "cover_image", "publish", "reading_time",
            "views", "status", "url",
        ]

    def get_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(obj.get_absolute_url()) if request else ""


class PostDetailSerializer(PostListSerializer):
    comments = CommentSerializer(many=True, source="comments.all", read_only=True)

    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + ["body", "comments", "meta_description"]
