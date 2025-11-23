from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase

# We use the APIClient for making requests to DRF views
from rest_framework.test import APIClient
from rest_framework import status

from .models import Post, Comment
from .serializers import PostListSerializer, PostWriteSerializer

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
    """Create and return a new user."""
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
# A. Model Tests
# ----------------------------------------------------------------------


class PostModelTests(TestCase):
    """Test basic functionality of the Post model."""

    def setUp(self):
        self.user = create_user(
            email="author@test.com", password="password123", first_name="A"
        )
        self.post = create_post(self.user, title="A Sample Post Title")

    def test_post_str_is_title(self):
        """Test the __str__ method returns the post title."""
        self.assertEqual(str(self.post), self.post.title)

    def test_slug_generation_on_save(self):
        """Test that the slug field is automatically generated from the title."""
        # The save() method runs on create_post
        self.assertEqual(self.post.slug, "a-sample-post-title")

    def test_post_creation_defaults(self):
        """Test default values are set correctly."""
        self.assertTrue(self.post.is_published)
        self.assertIsNotNone(self.post.created_at)


# ----------------------------------------------------------------------
# B. Public Post API Tests (GET Requests)
# ----------------------------------------------------------------------


class PublicPostAPITests(TestCase):
    """Test public access (unauthenticated) to post endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email="public@test.com", password="password123")
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

        # Check success status
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Check that only ONE post (the published one) is returned
        self.assertEqual(len(res.data), 1)
        # Check the correct post is in the list
        self.assertEqual(res.data[0]["title"], self.published_post.title)

    # --- DETAIL VIEW (/api/posts/<pk>/) ---

    def test_retrieve_published_post_detail_success(self):
        """Test GET /api/posts/<pk>/ returns a published post."""
        url = post_detail_url(self.published_post.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], self.published_post.title)
        # Check for nested Author data (via PostDetailSerializer)
        self.assertIn("author", res.data)
        self.assertIn(
            "content", res.data
        )  # Check that the detail view returned content

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
# C. Admin Post API Tests (Write & Admin Read Access)
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

        # Setup data
        self.post = create_post(
            self.regular_user, title="Admin Managed Post", is_published=False
        )
        self.payload = {
            "title": "New Post Title",
            "content": "The new content of the post.",
            "excerpt": "New excerpt.",
            "is_published": True,
        }

    # --- ADMIN READ ACCESS (GET) ---

    def test_admin_retrieve_all_posts_list(self):
        """Test GET /api/posts/ returns all posts (published and unpublished) to admin."""
        # The admin user is already set up and authenticated
        res = self.client.get(POST_LIST_CREATE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Should return both the created post (unpublished) and any other post
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], self.post.title)

    def test_admin_retrieve_unpublished_post_detail_success(self):
        """Test GET /api/posts/<pk>/ returns an unpublished post to admin."""
        url = post_detail_url(self.post.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data["is_published"])  # Must see the unpublished status

    # --- WRITE ACCESS (POST) ---

    def test_create_post_success(self):
        """Test POST /api/posts/ successfully creates a post and returns minimal response."""
        res = self.client.post(POST_LIST_CREATE_URL, self.payload)

        # 1. Assert Status
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # 2. Assert Minimal Response (ID/URL needed for redirection)
        self.assertIn("url", res.data)
        self.assertIn("message", res.data)

        # 3. Assert Model Creation and Author Assignment
        post = Post.objects.get(title=self.payload["title"])
        self.assertEqual(post.author, self.admin)  # Author must be the logged-in admin
        self.assertTrue(post.is_published)  # is_published must be set
        self.assertIn(str(post.id), res.data["url"])  # URL must contain the new ID

    def test_create_post_missing_title_fails(self):
        """Test POST fails if a required field like 'title' is missing."""
        bad_payload = self.payload.copy()
        del bad_payload["title"]

        res = self.client.post(POST_LIST_CREATE_URL, bad_payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", res.data)
        self.assertEqual(Post.objects.count(), 1)  # Only the setup post should exist

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
        # PUT requires all writeable fields
        full_payload = self.payload.copy()
        full_payload["title"] = new_title

        res = self.client.put(url, full_payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, new_title)
        self.assertTrue(self.post.is_published)  # Check that the field was updated
        self.assertEqual(
            self.post.author, self.regular_user
        )  # Author must remain unchanged

    def test_partial_update_post_PATCH_success(self):
        """Test PATCH /api/posts/<pk>/ partially updates a post."""
        url = post_detail_url(self.post.id)
        new_excerpt = "Only this was changed."
        payload = {"excerpt": new_excerpt}

        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertEqual(self.post.excerpt, new_excerpt)
        # Ensure other fields remain the same (e.g., title)
        self.assertNotEqual(self.post.title, new_excerpt)

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
        self.assertFalse(Post.objects.filter(id=self.post.id).exists())


# ----------------------------------------------------------------------
# D. Comment API Tests (Write & Permissions)
# ----------------------------------------------------------------------


class CommentAPITests(TestCase):
    """Test comment creation and management endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.author = create_user(
            email="commenter@test.com", password="password123", first_name="C"
        )
        self.other_user = create_user(
            email="other@test.com", password="password123", first_name="O"
        )
        self.admin = create_superuser(email="admin@test.com", password="adminpassword")

        self.post = create_post(self.author, title="Post with Comments")

        # Comment by the Author
        self.comment_by_author = create_comment(
            self.author, self.post, body="First comment by author", is_approved=False
        )

        # Comment by another user
        self.comment_by_other = create_comment(
            self.other_user,
            self.post,
            body="Second comment by other user",
            is_approved=True,
        )

        # Payload for creating a new comment
        self.comment_payload = {
            "post": self.post.id,  # Required Post ID
            "body": "A brand new comment body.",
        }

    # --- COMMENT CREATION (POST /api/posts/comments/) ---

    def test_create_comment_success(self):
        """Test POST /api/posts/comments/ creates a comment (IsAuthenticated)."""
        self.client.force_authenticate(user=self.author)
        res = self.client.post(COMMENT_CREATE_URL, self.comment_payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        comment = Comment.objects.get(body=self.comment_payload["body"])
        self.assertEqual(comment.author, self.author)  # Author must be set
        self.assertFalse(comment.is_approved)  # Should default to False as per model

    def test_create_comment_anonymous_forbidden(self):
        """Test POST /api/posts/comments/ is denied for anonymous users."""
        res = self.client.post(COMMENT_CREATE_URL, self.comment_payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_comment_invalid_post_fails(self):
        """Test creation fails if the post ID does not exist (Serializer validation)."""
        self.client.force_authenticate(user=self.author)
        bad_payload = self.comment_payload.copy()
        bad_payload["post"] = 99999  # Non-existent Post ID

        res = self.client.post(COMMENT_CREATE_URL, bad_payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("post", res.data)  # Check for validation error on 'post' field

    # --- COMMENT DETAIL RETRIEVAL (GET /api/posts/comments/<pk>/) ---

    def test_retrieve_comment_detail_public(self):
        """Test GET /api/posts/comments/<pk>/ allows anonymous access."""
        url = comment_detail_url(self.comment_by_author.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["body"], self.comment_by_author.body)

    # --- COMMENT MANAGEMENT (PUT/PATCH/DELETE) ---
    # These rely on the IsAuthorOrAdmin permission logic

    def test_update_comment_by_author_success(self):
        """Test PATCH allows the comment author to update the comment body."""
        self.client.force_authenticate(user=self.author)
        url = comment_detail_url(self.comment_by_author.id)
        new_body = "Updated by author."
        res = self.client.patch(url, {"body": new_body})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.comment_by_author.refresh_from_db()
        self.assertEqual(self.comment_by_author.body, new_body)

    def test_update_comment_by_other_user_forbidden(self):
        """Test PATCH is denied to a user who is not the author or admin."""
        self.client.force_authenticate(
            user=self.other_user
        )  # Other user tries to update author's comment
        url = comment_detail_url(self.comment_by_author.id)
        res = self.client.patch(url, {"body": "Attempted update"})

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_comment_by_admin_success(self):
        """Test PATCH allows the admin to update any comment (IsAuthorOrAdmin)."""
        self.client.force_authenticate(user=self.admin)
        url = comment_detail_url(self.comment_by_author.id)
        new_body = "Updated by admin."
        res = self.client.patch(url, {"body": new_body})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.comment_by_author.refresh_from_db()
        self.assertEqual(self.comment_by_author.body, new_body)

    def test_admin_can_approve_comment(self):
        """Test admin can set is_approved=True on PATCH."""
        self.client.force_authenticate(user=self.admin)
        url = comment_detail_url(self.comment_by_author.id)
        # Note: self.comment_by_author is initially is_approved=False
        res = self.client.patch(url, {"is_approved": True})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.comment_by_author.refresh_from_db()
        self.assertTrue(self.comment_by_author.is_approved)

    def test_author_cannot_approve_comment(self):
        """Test comment author cannot set is_approved=True (View logic check)."""
        self.client.force_authenticate(user=self.author)
        url = comment_detail_url(self.comment_by_author.id)

        res = self.client.patch(url, {"body": "New body", "is_approved": True})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.comment_by_author.refresh_from_db()
        # The view logic must discard the 'is_approved' field if the user is not staff
        self.assertFalse(self.comment_by_author.is_approved)

    def test_delete_comment_by_author_success(self):
        """Test DELETE allows the comment author to delete the comment."""
        self.client.force_authenticate(user=self.author)
        url = comment_detail_url(self.comment_by_author.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(id=self.comment_by_author.id).exists())

    def test_delete_comment_by_admin_success(self):
        """Test DELETE allows the admin to delete the comment."""
        self.client.force_authenticate(user=self.admin)
        url = comment_detail_url(self.comment_by_author.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(id=self.comment_by_author.id).exists())
