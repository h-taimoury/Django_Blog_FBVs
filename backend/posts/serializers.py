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
# --- Post Serializer ---
# ------------------------------------


# ----------------- 1. BASE/LIST SERIALIZER -----------------
# This serializer is used for the list view (/api/posts/).
class PostListSerializer(serializers.ModelSerializer):
    # Select related Author for the to-one relationship
    author = AuthorSerializer(read_only=True)
    url = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "title",
            "excerpt",
            "url",
            "updated_at",
        )
        read_only_fields = fields

    def get_url(self, obj):
        """Generates the combined slug-ID URL for the post."""
        return f"/posts/{obj.slug}-{obj.id}/"


# ----------------- 2. DETAIL SERIALIZER -----------------
# This serializer inherits all fields from PostSerializer and ADDS the comments field.
class PostDetailSerializer(PostListSerializer):
    # This field is NOT defined in the parent, so it is added here.
    # We define it using the prefetch_related optimization rule.
    comments = CommentSerializer(many=True, read_only=True)
    comment_count = serializers.SerializerMethodField()

    class Meta(PostListSerializer.Meta):
        # We inherit the Meta class and explicitly include the necessary fields in the field list
        fields = PostListSerializer.Meta.fields + (
            "content",
            "comments",
            "comment_count",
            "created_at",
        )
        read_only_fields = fields

    def get_comment_count(self, obj):
        """Returns the number of approved comments for the post."""
        # Only count approved comments for public display
        return obj.comments.filter(is_approved=True).count()


# ----------------- 3. Write SERIALIZER -----------------
class PostWriteSerializer(serializers.ModelSerializer):
    """
    Serializer used for creating (POST) and updating (PUT/PATCH) a Post.
    It includes all fields an Admin user is expected to provide or modify.
    """

    url = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ("title", "content", "excerpt", "is_published", "url")
        # We explicitly exclude 'author' here.
        # It is set automatically in the view (request.user).
        read_only_fields = ["url"]
        # Note: 'slug' is not included here because it's automatically generated
        # in the Post model's save() method.

    def get_url(self, obj):
        """Generates the combined slug-ID URL for the post."""
        return f"/posts/{obj.slug}-{obj.id}/"
