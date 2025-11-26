from django.db import models
from django.conf import (
    settings,
)  # Best practice to import the custom User model to use in other model.
from django.utils.text import slugify

# We reference the custom User model using settings.AUTH_USER_MODEL
# This ensures flexibility and correctness across Django versions.
User = settings.AUTH_USER_MODEL


class Post(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
    )

    # Essential post fields
    title = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, blank=True)
    content = models.TextField()
    excerpt = models.CharField(
        max_length=300,
        blank=True,
    )
    # Management fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Post"
        verbose_name_plural = "Posts"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Automatically generate a slug from the title
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class Comment(models.Model):
    # Links the comment to the post it belongs to
    # on_delete=models.CASCADE means if the Post is deleted, all its comments are also deleted.
    post = models.ForeignKey(Post, on_delete=models.CASCADE)

    # Links the comment to the user who wrote it
    # on_delete=models.SET_NULL means if the User is deleted, the comment remains, but the 'author' field is set to NULL.
    # This prevents the loss of comment history. 'null=True' is required for this.
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # Comment body
    body = models.TextField()

    # Management fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(default=False)  # For moderation

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Comment"
        verbose_name_plural = "Comments"

    def __str__(self):
        # Display the first 50 characters of the comment body
        body_snippet = self.body[:50].replace(
            "\n", " "
        )  # Safely get 50 chars and remove newlines

        return f"Comment: '{body_snippet}...' by {self.author.email if self.author else 'Deleted User'} on Post: '{self.post.title[:30]}...'"
