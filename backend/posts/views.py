from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Post, Comment
from .serializers import (
    PostListSerializer,
    PostDetailSerializer,
    PostWriteSerializer,
    CommentSerializer,
)
from .permissions import IsAdminOrReadOnly, IsAuthorOrAdmin

# ---  Post Views ---


@api_view(["GET", "POST"])
@permission_classes([IsAdminOrReadOnly])
def post_list_create(request):
    """
    GET: List published posts (public) or all posts (admin).
    POST: Create a new post (admin only).
    """
    if request.method == "GET":
        # Public users see published posts only
        if request.user.is_staff:
            queryset = Post.objects.all()
        else:
            queryset = Post.objects.filter(is_published=True)

        # Optimization: Select related user data and prefetch comments for efficient serialization
        queryset = queryset.select_related("author").order_by("-created_at")

        serializer = PostListSerializer(queryset, many=True)
        return Response(serializer.data)

    elif request.method == "POST":
        serializer = PostWriteSerializer(data=request.data)

        if serializer.is_valid():
            # 1. Save the post instance
            post_instance = serializer.save(author=request.user)
            post_url = f"/posts/{post_instance.slug}-{post_instance.id}/"
            response_data = {
                "url": post_url,
                "message": "Post created successfully.",
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAdminOrReadOnly])  # Controls PUT/PATCH/DELETE access
def post_detail(request, pk):
    """
    GET: Retrieve post (must be published, or admin).
    PUT/PATCH/DELETE: Update/Delete post (admin only).
    """

    # --- GET (Retrieve) ---
    if request.method == "GET":
        base_queryset = Post.objects.select_related("author").prefetch_related(
            "comment_set__author"
        )

        if not request.user.is_staff:
            # Public access: only published posts allowed
            post = get_object_or_404(base_queryset, pk=pk, is_published=True)
        else:
            # Admin access
            post = get_object_or_404(base_queryset, pk=pk)

        # When retrieving, we want the full nested data (including comments)
        serializer = PostDetailSerializer(post)
        return Response(serializer.data)

    # --- PUT/PATCH/DELETE (Admin Only) ---
    # IsAdminOrReadOnly ensures only staff users reach this point for unsafe methods

    elif request.method in ["PUT", "PATCH"]:
        post = get_object_or_404(Post, pk=pk)
        partial = request.method == "PATCH"
        write_serializer = PostWriteSerializer(post, data=request.data, partial=partial)

        if write_serializer.is_valid():
            write_serializer.save()

            # 3. Return a success status with no data (most efficient)
            return Response(
                {"message": "Post updated successfully."}, status=status.HTTP_200_OK
            )

        return Response(write_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        post = get_object_or_404(Post, pk=pk)
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- 3. Comment Views ---


@api_view(["POST"])
@permission_classes([IsAuthenticated])  # Only authenticated users can create comments
def comment_create(request):
    """
    POST: Create a new comment (authenticated users only).
    The post ID is provided in the request body.
    """
    # The CommentSerializer's 'validate_post' method ensures the post ID is valid.
    serializer = CommentSerializer(data=request.data)

    if serializer.is_valid():
        # Automatically set the author to the requesting authenticated user
        serializer.save(author=request.user)
        # Note: The 'is_approved' field defaults to False in the model.
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthorOrAdmin])
def comment_detail(request, pk):
    """
    GET, PUT, PATCH, DELETE: Restricted to the author or an admin.
    """
    comment = get_object_or_404(Comment, pk=pk)

    # --- MANUAL OBJECT-LEVEL PERMISSION CHECK ---
    # In Function-Based Views (FBVs), DRF only runs has_permission automatically.
    # We must manually run has_object_permission after retrieving the 'comment' object.

    permission_checker = IsAuthorOrAdmin()

    if not permission_checker.has_object_permission(request, comment_detail, comment):
        # This will catch non-author/non-admin users and return 403 Forbidden.
        # Note: Unauthenticated users are already caught by the @permission_classes
        # decorator (via IsAuthorOrAdmin.has_permission), which returns 401 Unauthorized.
        return Response(
            {
                "detail": "Permission denied. You must be the author or an administrator to access this comment."
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # --- RESTRICTED ACTIONS (Only Author/Admin can proceed from here) ---

    # --- GET (Retrieve) ---
    if request.method == "GET":
        # The permission check above already restricts this method.
        serializer = CommentSerializer(comment)
        return Response(serializer.data)

    # --- PUT/PATCH (Update) ---
    elif request.method in ["PUT", "PATCH"]:
        partial = request.method == "PATCH"
        serializer = CommentSerializer(comment, data=request.data, partial=partial)

        if serializer.is_valid():
            # If a non-admin is updating, ensure they cannot set is_approved=True
            if not request.user.is_staff:
                # Discard any attempt to modify 'is_approved' unless the user is staff
                if "is_approved" in serializer.validated_data:
                    del serializer.validated_data["is_approved"]

            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # --- DELETE ---
    elif request.method == "DELETE":
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# # --- 1. Define QuerySet based on Method (Conditional Optimization) ---
#     if request.method == "GET":
#         # FULL OPTIMIZATION: Needed for PostDetailSerializer to avoid N+1 queries
#         # Fetches Author, Comments, and Comment Authors efficiently (approx. 3 queries total)
#         base_queryset = Post.objects.select_related("author").prefetch_related("comments__author")
#     else:
#         # MINIMAL QUERYSET: For PUT/PATCH/DELETE. We only need the Post instance itself.
#         # Stripping prefetch_related and select_related eliminates unnecessary database activity.
#         base_queryset = Post.objects.all()
