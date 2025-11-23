from django.urls import path
from .views import post_list_create, post_detail, comment_create, comment_detail

urlpatterns = [
    # ----------------------------------------------------------------------
    # 1. POST Endpoints
    # ----------------------------------------------------------------------
    # Endpoint: /api/posts/
    # Methods: GET (List published/all posts), POST (Create post - Admin only)
    path("", post_list_create, name="post-list-create"),
    # ----------------------------------------------------------------------
    # Endpoint: /api/posts/<int:pk>/
    # Methods: GET (Retrieve), PUT/PATCH (Update - Admin only), DELETE (Delete - Admin only)
    # The frontend uses this ID (pk) for the API call, ignoring the slug part of the user-facing URL.
    path("<int:pk>/", post_detail, name="post-detail"),
    # ----------------------------------------------------------------------
    # 2. COMMENT Endpoints
    # ----------------------------------------------------------------------
    # Endpoint: /api/posts/comments/
    # Methods: POST (Create comment - Authenticated users only)
    path("comments/", comment_create, name="comment-create"),
    # ----------------------------------------------------------------------
    # Endpoint: /api/posts/comments/<int:pk>/
    # Methods: GET, PUT, PATCH and DELETE (Author or Admin only)
    path(
        "comments/<int:pk>/",
        comment_detail,
        name="comment-detail",
    ),
    # ----------------------------------------------------------------------
]
