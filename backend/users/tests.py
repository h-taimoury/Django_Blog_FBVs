from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase

# We use the APIClient for making requests to DRF views
from rest_framework.test import APIClient
from rest_framework import status

# Get the custom user model dynamically
User = get_user_model()

# --- URL Name Definitions ---
# These names should match the names defined in your urls.py for users app
USERS_URL = reverse("users")  # /api/users/
REGISTER_URL = reverse("register")  # /api/users/register/ (Custom View)
LOGIN_URL = reverse("login")  # /api/users/login/ (Custom View)


# Helper function to generate URL for detail views (e.g., /api/users/1/)
def detail_url(user_id):
    return reverse("user-detail", kwargs={"pk": user_id})


# Helper function to generate URL for the /me/ endpoint
ME_URL = reverse("me")  # /api/users/me/

# --- Test Case Setup ---


class PublicUserAPITests(TestCase):
    """Test the public endpoints that don't require authentication."""

    def setUp(self):
        # Initialize an unauthenticated client
        self.client = APIClient()
        self.payload = {
            "email": "testuser@example.com",
            "password": "StrongPassword123",
            "first_name": "Test",
            "last_name": "User",
        }

    def test_create_valid_user_success(self):
        """Test creating a user via POST to /api/users/register/ works and returns a token."""
        res = self.client.post(REGISTER_URL, self.payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # Check if the user was created in the database
        user = User.objects.get(email=self.payload["email"])
        self.assertTrue(user.check_password(self.payload["password"]))

        # Check response structure
        self.assertIn("token", res.data)
        self.assertNotIn("password", res.data)  # Crucial: Password must be write-only

    def test_create_user_missing_password_fails(self):
        """Test creating a user with a missing required password fails validation."""
        bad_payload = {
            "email": "bad@example.com",
            "first_name": "Bad",
            "last_name": "User",
            # 'password' is missing
        }
        res = self.client.post(REGISTER_URL, bad_payload, format="json")

        # 1. Assert failure status code
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        # 2. Assert error message for 'password' field is present
        self.assertIn("password", res.data)
        self.assertEqual(User.objects.count(), 0)  # No user should be created

    def test_create_user_missing_email_fails(self):
        """Test creating a user with a missing required email fails validation."""
        bad_payload = {
            # 'email' is missing
            "password": "TestPassword123",
            "first_name": "Bad",
            "last_name": "User",
        }
        res = self.client.post(REGISTER_URL, bad_payload, format="json")

        # 1. Assert failure status code
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        # 2. Assert error message for 'email' field is present
        self.assertIn("email", res.data)
        self.assertEqual(User.objects.count(), 0)  # No user should be created

    def test_login_user_success(self):
        """Test logging in an existing user via POST to /api/users/login/."""
        # Create the user first
        User.objects.create_user(**self.payload)

        login_payload = {
            "email": self.payload["email"],
            "password": self.payload["password"],
        }
        res = self.client.post(LOGIN_URL, login_payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        self.assertNotIn("password", res.data)


class PrivateUserMeTests(TestCase):
    """Test the /api/users/me/ endpoint requiring authentication."""

    def setUp(self):
        # Create a standard user
        self.user = User.objects.create_user(
            email="auth@example.com",
            password="TestPassword123",
            first_name="Auth",
            last_name="User",
        )
        # Initialize an authenticated client
        self.client = APIClient()
        # You'll need to mock the authentication, usually by forcing a login or setting the token header.
        # Assuming you use SimpleJWT, we will just force login for simplicity in testing.
        self.client.force_authenticate(user=self.user)

    def test_retrieve_me_success(self):
        """Test GET /api/users/me/ returns authenticated user's details."""
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], self.user.email)
        self.assertEqual(res.data["first_name"], "Auth")
        self.assertNotIn("password", res.data)

    def test_update_me_username_success(self):
        """Test PATCH /api/users/me/ updates fields like first_name."""
        new_name = "NewAuthName"
        payload = {"first_name": new_name}
        res = self.client.patch(ME_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, new_name)

    def test_update_me_password_success(self):
        """Test PATCH /api/users/me/ can update the password."""
        new_password = "NewSecurePassword456"
        payload = {"password": new_password}
        res = self.client.patch(ME_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        # Check that the password was hashed and changed
        self.assertTrue(self.user.check_password(new_password))

    def test_update_me_read_only_fields_ignored(self):
        """Test PATCH /api/users/me/ ignores attempts to modify read-only fields."""
        original_created_at = self.user.created_at
        payload = {
            "id": 999,
            "created_at": "2000-01-01T00:00:00Z",
            "email": "new@example.com",  # include a valid field to make the request pass
        }
        res = self.client.patch(ME_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        # Verify that ID was NOT changed
        self.assertNotEqual(self.user.id, 999)
        # Verify that created_at was NOT changed (it should be very close to the original)
        self.assertEqual(self.user.created_at.date(), original_created_at.date())
        # Verify that the valid field WAS changed
        self.assertEqual(self.user.email, "new@example.com")


class PrivateUserAdminTests(TestCase):
    """Test admin-only endpoints (/api/users/, /api/users/:id/)."""

    def setUp(self):
        # Initialize client
        self.client = APIClient()

        # Create Admin User
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPassword123",
            first_name="System",
            last_name="Admin",
        )
        # Create Regular User
        self.regular_user = User.objects.create_user(
            email="regular@example.com",
            password="RegularPassword123",
            first_name="Jane",
            last_name="Doe",
        )
        # Authenticate as Admin
        self.client.force_authenticate(user=self.admin_user)

    # --- LIST ENDPOINTS (Admin Only) ---

    def test_list_users_admin_allowed(self):
        """Test GET /api/users/ allows admin access."""
        res = self.client.get(USERS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Should return at least 2 users (admin and regular)
        self.assertEqual(len(res.data), 2)
        # Crucial security check: Ensure no user password is leaked
        self.assertNotIn("password", res.data[0])

    def test_list_users_regular_user_forbidden(self):
        """Test GET /api/users/ denies regular user access."""
        self.client.force_authenticate(user=self.regular_user)
        res = self.client.get(USERS_URL)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # --- DETAIL ENDPOINTS (Admin Only) ---

    def test_retrieve_user_detail_admin_allowed(self):
        """Test GET /api/users/:id/ allows admin access."""
        url = detail_url(self.regular_user.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], self.regular_user.email)

    def test_update_user_detail_admin_allowed_PUT_method(self):
        """Test PUT /api/users/:id/ allows admin to update."""
        new_last_name = "Smith"
        # Perform a full PUT, so all required fields must be present which are email and password fields. Other fields are not required and remain the same if not included.
        payload = {
            "email": self.regular_user.email,  # Must be included for PUT
            "first_name": self.regular_user.first_name,
            "last_name": new_last_name,
            "is_staff": True,
            "is_active": self.regular_user.is_active,
            "password": "SomePassword123",  # Must be included because it's required=True, even if unchanged
        }
        url = detail_url(self.regular_user.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.last_name, new_last_name)
        self.assertTrue(self.regular_user.is_staff)

    def test_update_user_detail_admin_allowed_PATCH_method(self):
        """Test PATCH /api/users/:id/ allows admin to update."""
        new_last_name = "Smith"
        # Perform a PATCH request, so we only need to include fields we want to update. We don't need to even include required fields which are email and password.
        payload = {
            "last_name": new_last_name,
        }
        url = detail_url(self.regular_user.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.last_name, new_last_name)

    def test_delete_user_admin_allowed(self):
        """Test DEL /api/users/:id/ allows admin to delete."""
        user_count_before = User.objects.count()
        url = detail_url(self.regular_user.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(User.objects.count(), user_count_before - 1)
        self.assertFalse(User.objects.filter(id=self.regular_user.id).exists())
