from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase

# We use the APIClient for making requests to DRF views
from rest_framework.test import APIClient
from rest_framework import status

from .models import Post, Comment

# Get the custom user model dynamically
User = get_user_model()

# --- URL Name Definitions ---
# These names match your posts/urls.py
POST_LIST_CREATE_URL = reverse("post-list-create")
COMMENT_CREATE_URL = reverse("comment-create")


# Helper function to generate URL for detail views (e.g., /api/posts/1/)
def post_detail_url(post_id):
    return reverse("post-detail", kwargs={"pk": post_id})


# Helper function to generate URL for comment detail views (e.g., /api/posts/comments/1/)
def comment_detail_url(comment_id):
    return reverse("comment-detail", kwargs={"pk": comment_id})


# --- Helper Functions for Test Setup ---


def create_user(**params):
    """Create and return a new regular user."""
    return User.objects.create_user(**params)


def create_superuser(**params):
    """Create and return a new admin user."""
    return User.objects.create_superuser(**params)


def create_post(user, **params):
    """Create and return a new post, setting required fields if missing."""
    defaults = {
        "title": "Default Test Post Title",
        "content": "Default test content.",
        "excerpt": "Default excerpt.",
        "is_published": True,
    }
    defaults.update(params)
    return Post.objects.create(author=user, **defaults)


def create_comment(user, post, **params):
    """Create and return a new comment."""
    defaults = {
        "body": "Default test comment body.",
        "is_approved": True,
    }
    defaults.update(params)
    return Comment.objects.create(author=user, post=post, **defaults)


# ----------------------------------------------------------------------
# A. Public Post API Tests (Integration Tests for Read Access)
# ----------------------------------------------------------------------


class PublicPostAPITests(TestCase):
    """Test public access (unauthenticated) to post endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email="public@test.com", password="password123")
        # Post created by a regular user (should not matter as long as it exists)
        self.published_post = create_post(
            self.user, title="Published Post", is_published=True
        )
        self.unpublished_post = create_post(
            self.user, title="Unpublished Post", is_published=False
        )

    # --- LIST VIEW (/api/posts/) ---

    def test_retrieve_published_posts_list(self):
        """Test GET /api/posts/ returns only published posts to public users."""
        res = self.client.get(POST_LIST_CREATE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Should only return the ONE published post
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], self.published_post.title)

    # --- DETAIL VIEW (/api/posts/<pk>/) ---

    def test_retrieve_published_post_detail_success(self):
        """Test GET /api/posts/<pk>/ returns a published post."""
        url = post_detail_url(self.published_post.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_retrieve_unpublished_post_detail_404(self):
        """Test GET /api/posts/<pk>/ returns 404 for unpublished posts to public users."""
        url = post_detail_url(self.unpublished_post.id)
        res = self.client.get(url)

        # The view explicitly filters by is_published=True for non-staff users
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # --- WRITE OPERATIONS (FORBIDDEN) ---

    def test_post_is_forbidden_for_anonymous_user(self):
        """Test POST /api/posts/ is denied for anonymous users (requires IsAdminOrReadOnly)."""
        res = self.client.post(POST_LIST_CREATE_URL, {"title": "Attempt"})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


# ----------------------------------------------------------------------
# B. Admin Post API Tests (Integration Tests for Admin/Write Access)
# ----------------------------------------------------------------------


class AdminPostAPITests(TestCase):
    """Test write and admin-only read access to post endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.admin = create_superuser(email="admin@test.com", password="adminpassword")
        self.regular_user = create_user(
            email="regular@test.com", password="userpassword"
        )
        # Authenticate as Admin
        self.client.force_authenticate(user=self.admin)

        # Setup data: FIX APPLIED - Post creator is now the Admin
        self.post = create_post(
            self.admin, title="Admin Managed Post", is_published=False
        )
        self.payload = {
            "title": "New Post Title",
            "content": (
                "<h2>Section Header</h2>"
                "<p>This is the first paragraph. It contains some <strong>bold text</strong>.</p>"
                "<ul><li>Item one</li><li>Item two</li></ul>"
                '<p><a href="http://safe-link.com">Read More</a></p>'
            ),
            "excerpt": "New excerpt.",
            "is_published": True,
        }

    # --- ADMIN READ ACCESS (GET) ---

    def test_admin_retrieve_unpublished_post_detail_success(self):
        """Test GET /api/posts/<pk>/ returns an unpublished post to admin."""
        url = post_detail_url(self.post.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(
            self.post.is_published
        )  # Check that the correct post is returned

    # --- WRITE ACCESS (POST) ---

    def test_create_post_success_and_minimal_response(self):
        """Test POST /api/posts/ successfully creates a post and returns minimal response."""
        res = self.client.post(POST_LIST_CREATE_URL, self.payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Assert Minimal Response (URL needed for redirection)
        self.assertIn("url", res.data)
        self.assertIn("message", res.data)

    def test_create_post_sanitizes_content_stripping_script_tag(self):
        """Test POST /api/posts/ successfully strips malicious <script> tags from 'content'."""
        malicious_content = (
            "<h1>Safe Title</h1><script>alert('XSS attempt')</script><p>Safe text.</p>"
        )
        safe_content_expected = "<h1>Safe Title</h1>alert('XSS attempt')<p>Safe text.</p>"  # The <script> tag is removed

        payload = self.payload.copy()
        payload["content"] = malicious_content

        # Ensure we are authenticated as admin
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(POST_LIST_CREATE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Retrieve the post directly from the database
        post = Post.objects.get(title=payload["title"])
        # Assert that the dangerous script tag was stripped
        # Note: If your bleach config allows <h1>, adjust safe_content_expected accordingly
        self.assertNotIn("<script>", post.content.lower())
        self.assertIn("safe title", post.content.lower())
        self.assertIn("<p>", post.content.lower())
        self.assertNotEqual(post.content, malicious_content)

        # Optional: Assert the cleaned content matches the expected safe version
        self.assertEqual(post.content, safe_content_expected)

    def test_create_post_regular_user_forbidden(self):
        """Test POST /api/posts/ is denied for regular authenticated users."""
        self.client.force_authenticate(user=self.regular_user)
        res = self.client.post(POST_LIST_CREATE_URL, self.payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # --- UPDATE ACCESS (PUT/PATCH) ---

    def test_full_update_post_PUT_success(self):
        """Test PUT /api/posts/<pk>/ fully updates a post."""
        url = post_detail_url(self.post.id)
        new_title = "Fully Updated Title"
        full_payload = self.payload.copy()
        full_payload["title"] = new_title

        res = self.client.put(url, full_payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, new_title)

    def test_update_post_regular_user_forbidden(self):
        """Test PUT/PATCH is denied for regular authenticated users (IsAdminOrReadOnly)."""
        self.client.force_authenticate(user=self.regular_user)
        url = post_detail_url(self.post.id)
        res = self.client.patch(url, {"title": "Unauthorized"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # --- DELETE ACCESS (DELETE) ---

    def test_delete_post_success(self):
        """Test DELETE /api/posts/<pk>/ successfully deletes a post."""
        url = post_detail_url(self.post.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)


# ----------------------------------------------------------------------
# C. Comment API Tests (Integration Tests for Comment Management)
# ----------------------------------------------------------------------


class CommentAPITests(TestCase):
    """Test comment creation and management endpoints."""

    def setUp(self):
        self.client = APIClient()
        # author is the non-admin user who leaves the comment
        self.author = create_user(
            email="commenter@test.com", password="password123", first_name="C"
        )
        # Added a user who is neither the author nor an admin
        self.other_user = create_user(
            email="otheruser@test.com", password="password123", first_name="O"
        )
        self.admin = create_superuser(email="admin@test.com", password="adminpassword")

        # Post created by the Admin (aligned with project rules that only admins can create posts)
        self.post = create_post(self.admin, title="Post with Comments")

        # Comment by the Author
        self.comment = create_comment(
            self.author, self.post, body="First comment by author", is_approved=False
        )

        # Payload for creating a new comment
        self.comment_payload = {
            "post": self.post.id,
            "body": "A brand new comment body.",
        }

    # --- COMMENT CREATION (POST /api/posts/comments/) ---

    def test_create_comment_authenticated_user_success(self):
        """Test POST /api/posts/comments/ creates a comment (IsAuthenticated)."""
        self.client.force_authenticate(user=self.author)
        res = self.client.post(COMMENT_CREATE_URL, self.comment_payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        comment = Comment.objects.get(body=self.comment_payload["body"])
        self.assertEqual(comment.author, self.author)
        self.assertFalse(comment.is_approved)

    def test_create_comment_anonymous_forbidden(self):
        """Test POST /api/posts/comments/ is denied for anonymous users."""
        res = self.client.post(COMMENT_CREATE_URL, self.comment_payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- COMMENT DETAIL RETRIEVAL (GET /api/posts/comments/<pk>/) ---
    # NOTE: These tests now reflect the IsAuthorOrAdmin restriction on GET

    def test_retrieve_comment_detail_by_author_success(self):
        """Test GET allows the comment author to retrieve the comment."""
        self.client.force_authenticate(user=self.author)
        url = comment_detail_url(self.comment.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_retrieve_comment_detail_by_admin_success(self):
        """Test GET allows the admin to retrieve the comment."""
        self.client.force_authenticate(user=self.admin)
        url = comment_detail_url(self.comment.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_retrieve_comment_detail_anonymous_forbidden(self):
        """Test GET is denied for anonymous users (expects 401 UNAUTHORIZED)."""
        # Client is not authenticated
        url = comment_detail_url(self.comment.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_comment_detail_non_author_forbidden(self):
        """Test GET is denied for an authenticated user who is neither author nor admin (expects 403 FORBIDDEN)."""
        self.client.force_authenticate(user=self.other_user)
        url = comment_detail_url(self.comment.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # --- COMMENT MANAGEMENT (PUT/PATCH/DELETE) ---

    def test_update_comment_by_author_success(self):
        """Test PATCH allows the comment author to update the comment body."""
        self.client.force_authenticate(user=self.author)
        url = comment_detail_url(self.comment.id)
        new_body = "Updated by author."
        res = self.client.patch(url, {"body": new_body})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.body, new_body)

    def test_update_comment_by_non_author_forbidden(self):
        """Test PATCH is denied to a user who is not the author or admin."""
        self.client.force_authenticate(user=self.other_user)
        url = comment_detail_url(self.comment.id)
        res = self.client.patch(url, {"body": "Attempted update"})

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_comment_by_admin_success(self):
        """Test PATCH allows the admin to update any comment."""
        self.client.force_authenticate(user=self.admin)
        url = comment_detail_url(self.comment.id)
        new_body = "Updated by admin."
        res = self.client.patch(url, {"body": new_body})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_author_cannot_approve_comment(self):
        """Test comment author cannot set is_approved=True (checking view permission logic)."""
        self.client.force_authenticate(user=self.author)
        url = comment_detail_url(self.comment.id)

        self.client.patch(url, {"is_approved": True})

        self.comment.refresh_from_db()
        self.assertFalse(self.comment.is_approved)

    def test_delete_comment_by_author_success(self):
        """Test DELETE allows the comment author to delete the comment."""
        self.client.force_authenticate(user=self.author)
        url = comment_detail_url(self.comment.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_comment_by_admin_success(self):
        """Test DELETE allows the admin to delete the comment."""
        self.client.force_authenticate(user=self.admin)
        url = comment_detail_url(self.comment.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_comment_by_non_author_forbidden(self):
        """Test DELETE is denied to a user who is not the author or admin."""
        self.client.force_authenticate(user=self.other_user)
        url = comment_detail_url(self.comment.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
