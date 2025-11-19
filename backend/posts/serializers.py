from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Post, Comment

# --- Setup ---
User = get_user_model()

# --- Helper Serializers ---


class AuthorSerializer(serializers.ModelSerializer):
    """Minimal serializer for displaying the Post/Comment author."""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "full_name")
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name()


# ------------------------------------
# --- Comment Serializer ---
# ------------------------------------


class CommentSerializer(serializers.ModelSerializer):
    # This will be used for displaying the author on GET requests
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Comment
        # 'post' field will be required for POST requests to link to the Post ID
        # 'is_approved' is only writable by admins
        fields = ("id", "post", "author", "body", "created_at", "is_approved")
        read_only_fields = ("id", "author", "created_at")

    # We add validation to ensure the 'post' exists before creation
    def validate_post(self, value):
        """Checks if the Post ID provided in the 'post' field exists."""
        try:
            Post.objects.get(pk=value.id)
        except Post.DoesNotExist:
            raise serializers.ValidationError("Cannot comment on a non-existent post.")
        return value


# ------------------------------------
# --- Main Post Serializer ---
# ------------------------------------


class PostSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    url = serializers.SerializerMethodField()

    # Use the full CommentSerializer for nested representation when retrieving a single Post
    comments = CommentSerializer(many=True, read_only=True)
    comment_count = serializers.SerializerMethodField()

    # Explicitly define slug to allow it to be ignored during POST/PATCH
    slug = serializers.SlugField(max_length=200, required=False, allow_blank=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "url",
            "author",
            "title",
            "content",
            "slug",
            "is_published",
            "created_at",
            "updated_at",
            "comments",
            "comment_count",
        )
        read_only_fields = (
            "id",
            "author",
            "slug",
            "created_at",
            "updated_at",
            "comment_count",
        )

    def get_url(self, obj):
        """Generates the combined slug-ID URL for the post."""
        return f"/posts/{obj.slug}-{obj.id}/"

    def get_comment_count(self, obj):
        """Returns the number of approved comments for the post."""
        # Only count approved comments for public display
        return obj.comments.filter(is_approved=True).count()
