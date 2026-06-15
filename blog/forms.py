from django import forms
from django.contrib.auth.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field
from .models import Comment, Post, Profile, Newsletter, Contact


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["name", "email", "body"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Your name"}),
            "email": forms.EmailInput(attrs={"placeholder": "your@email.com"}),
            "body": forms.Textarea(attrs={"rows": 4, "placeholder": "Write your comment..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Post Comment", css_class="btn-post"))


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = [
            "title", "category", "cover_image", "excerpt",
            "body", "tags", "status", "featured", "allow_comments",
            "meta_description",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "title",
            Row(Column("category"), Column("status")),
            "cover_image",
            "excerpt",
            "body",
            "tags",
            Row(Column("featured"), Column("allow_comments")),
            "meta_description",
            Submit("submit", "Save Post", css_class="btn-save"),
        )


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = Profile
        fields = ["avatar", "bio", "website", "twitter", "github", "location", "newsletter_subscribed"]

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)
        if instance:
            self.fields["first_name"].initial = instance.user.first_name
            self.fields["last_name"].initial = instance.user.last_name
            self.fields["email"].initial = instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.user.first_name = self.cleaned_data["first_name"]
        profile.user.last_name = self.cleaned_data["last_name"]
        profile.user.email = self.cleaned_data["email"]
        if commit:
            profile.user.save()
            profile.save()
        return profile


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = Newsletter
        fields = ["email"]
        widgets = {"email": forms.EmailInput(attrs={"placeholder": "Enter your email"})}


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ["name", "email", "subject", "message"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Send Message", css_class="btn-send"))


class SearchForm(forms.Form):
    query = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Search posts...", "class": "search-input"}),
    )
