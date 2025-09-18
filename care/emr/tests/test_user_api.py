from io import BytesIO
from secrets import choice
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from care.emr.resources.patient.spec import GenderChoices
from care.emr.resources.user.spec import UserTypeOptions, UserTypeRoleMapping
from care.security.permissions.user import UserPermissions
from care.utils.tests.base import CareAPITestBase


class UserviewTestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.super_user = self.create_super_user(
            username="superuser", first_name="Super", last_name="User"
        )
        self.organization = self.create_organization(
            user=self.super_user, name="Parent Organization", org_type="govt"
        )
        self.user = self.create_user(
            username="testuser",
            first_name="Test",
            last_name="User",
            email="user@example.com",
            user_type=UserTypeOptions.administrator,
            geo_organization=self.organization,
            gender=GenderChoices.non_binary,
            phone_number="1234432100",
        )

        self.administrator_role = self.create_role_with_permissions(
            permissions=[
                UserPermissions.can_create_user.name,
                UserPermissions.can_list_user.name,
            ],
        )
        for user_type in UserTypeOptions:
            role_name = UserTypeRoleMapping[user_type.value].value.name
            self.create_role(
                name=role_name,
                is_system=True,
            )
        self.url = reverse("users-list")
        self.user_data = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "testuser@example.com",
            "password": "ComplexP@ssw0rd",
            "user_type": choice(list(UserTypeOptions)).value,
            "gender": GenderChoices.non_binary,
            "geo_organization": self.organization.external_id,
            "phone_number": "1234567890",
        }

    def get_user_detail_url(self, username):
        return reverse("users-detail", kwargs={"username": username})

    # Test case for listing users
    def test_list_users_as_super_user(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(self.url)
        self.create_user(username="deleteduser", deleted=True)
        self.assertEqual(response.status_code, 200)
        # Check that all returned users have deleted=False
        self.assertTrue(
            all(user.get("deleted") is False for user in response.data["results"])
        )

    def test_list_users_as_user_with_permission(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        # Check that all returned users have deleted=False
        self.assertTrue(
            all(user.get("deleted") is False for user in response.data["results"])
        )

    # Test case for creating users
    def test_create_user_as_super_user(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.post(self.url, self.user_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "newuser")
        get_response = self.client.get(self.get_user_detail_url("newuser"))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_user_as_user_with_permission(self):
        self.attach_role_organization_user(
            self.organization, self.user, self.administrator_role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, self.user_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "newuser")
        get_response = self.client.get(self.get_user_detail_url("newuser"))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_user_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, self.user_data, format="json")
        self.assertContains(
            response, "You do not have permission to create Users", status_code=403
        )
        self.assertEqual(response.status_code, 403)

    def test_create_user_with_invalid_username(self):
        self.client.force_authenticate(user=self.super_user)
        invalid_user_data = self.user_data.copy()
        invalid_user_data["username"] = "invalid username"
        response = self.client.post(self.url, invalid_user_data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Username can only contain alpha numeric values, dashes ( - ) and underscores ( _ )",
            status_code=400,
        )

    def test_create_user_with_existing_username(self):
        self.client.force_authenticate(user=self.super_user)

        existing_user_data = self.user_data.copy()
        existing_user_data["username"] = self.user.username
        response = self.client.post(self.url, existing_user_data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Username already exists", status_code=400)

    def test_create_user_with_existing_email(self):
        self.client.force_authenticate(user=self.super_user)
        existing_user_data = self.user_data.copy()
        existing_user_data["email"] = self.user.email
        response = self.client.post(self.url, existing_user_data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Email already exists", status_code=400)

    def test_create_user_with_invalid_email(self):
        self.client.force_authenticate(user=self.super_user)
        invalid_user_data = self.user_data.copy()
        invalid_user_data["email"] = "invalid-email"
        response = self.client.post(self.url, invalid_user_data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Invalid Email", status_code=400)

    def test_create_user_with_existing_phone_number(self):
        self.client.force_authenticate(user=self.super_user)
        existing_user_data = self.user_data.copy()
        existing_user_data["phone_number"] = self.user.phone_number
        response = self.client.post(self.url, existing_user_data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Phone Number already exists", status_code=400)

    def test_create_user_invalid_password(self):
        self.client.force_authenticate(user=self.super_user)
        invalid_user_data = self.user_data.copy()
        invalid_user_data["password"] = "12345"
        response = self.client.post(self.url, invalid_user_data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Password is too weak", status_code=400)

    def test_create_user_with_empty_data(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 400)

    # Test cases for update user details
    "Only super user and the user themselves can update user details"

    def test_update_user_as_super_user(self):
        self.client.force_authenticate(user=self.super_user)
        update_data = self.user_data.copy()
        update_data["first_name"] = "Updated"
        update_data["last_name"] = "User"
        response = self.client.put(
            self.get_user_detail_url(self.user.username),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_user_detail_url(self.user.username))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["first_name"], "Updated")
        self.assertEqual(get_response.data["last_name"], "User")

    def test_update_user_as_self(self):
        self.client.force_authenticate(user=self.user)
        update_data = self.user_data.copy()
        update_data["first_name"] = "Updated"
        update_data["last_name"] = "User"
        response = self.client.put(
            self.get_user_detail_url(self.user.username),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_user_detail_url(self.user.username))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["first_name"], "Updated")
        self.assertEqual(get_response.data["last_name"], "User")

    def test_update_user_as_other_user(self):
        other_user = self.create_user(username="otheruser")
        self.client.force_authenticate(user=other_user)
        update_data = self.user_data.copy()
        update_data["first_name"] = "Updated"
        update_data["last_name"] = "User"
        response = self.client.put(
            self.get_user_detail_url(self.user.username),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "You do not have permission to update this user", status_code=403
        )

    def test_update_user_with_invalid_data(self):
        self.client.force_authenticate(user=self.super_user)
        update_data = {
            "first_name": "Updated",
            "last_name": "User",
            "email": "invalid-email",
        }
        response = self.client.put(
            self.get_user_detail_url(self.user.username),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_update_user_geo_organization(self):
        new_organization = self.create_organization(
            name="New Organization", org_type="govt"
        )
        self.client.force_authenticate(user=self.user)
        update_data = self.user_data.copy()
        update_data["geo_organization"] = new_organization.external_id
        response = self.client.put(
            self.get_user_detail_url(self.user.username),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_user_detail_url(self.user.username))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["geo_organization"]["id"],
            str(new_organization.external_id),
        )

    # Test cases for delete user
    "Only super user can delete a user, if the user has logged in before, it will be marked as deleted"

    def test_delete_user_with_login_history_as_super_user(self):
        """Test that deleting a user with login history performs a soft delete."""
        # Create user with login history
        logineduser = self.create_user(username="loginuser")
        logineduser.last_login = timezone.now()
        logineduser.save()
        # Delete the user as superuser
        self.client.force_authenticate(user=self.super_user)
        url = self.get_user_detail_url("loginuser")
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        logineduser.refresh_from_db()
        self.assertTrue(logineduser.deleted)

    def test_delete_user_without_login_history_as_super_user(self):
        """Test that deleting a user without login history performs a hard delete."""
        # Create user without login history
        self.create_user(username="nologineduser")
        # Delete the user as superuser
        self.client.force_authenticate(user=self.super_user)
        url = self.get_user_detail_url("nologineduser")
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        # For a hard delete, we should check if the user no longer exists in the database
        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 404)
        self.assertContains(
            get_response, "No User matches the given query.", status_code=404
        )

    def test_delete_user_login_history_without_permission(self):
        """Test that regular users cannot delete other users."""
        # Create user with login history
        logineduser = self.create_user(username="loginuser")
        logineduser.last_login = timezone.now()
        logineduser.save()
        # Attempt to delete the user as a regular user
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.get_user_detail_url("loginuser"))
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "You do not have permission to delete this user", status_code=403
        )

    def test_delete_user_without_login_history_without_permission(self):
        """Test that regular users cannot delete other users without login history."""
        # Create user without login history
        self.create_user(username="nologineduser")
        # Attempt to delete the user as a regular user
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.get_user_detail_url("nologineduser"))
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "You do not have permission to delete this user", status_code=403
        )

    #   Test cases for filtering users
    def test_filter_users_by_username(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(self.url, {"username": "testuser"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["username"], "testuser")

    def test_filter_users_by_email(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(self.url, {"email": "user@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)

    def test_filter_users_by_phone_number(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(self.url, {"phone_number": "1234432100"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["phone_number"], "1234432100")

    def test_filter_users_by_user_type(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(
            self.url, {"user_type": UserTypeOptions.administrator.value}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["user_type"],
            UserTypeOptions.administrator.value,
        )

    # Test cases for checking username availability

    def test_check_username_availability_available(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(
            reverse("users-check-availability", kwargs={"username": "availableuser"})
        )
        self.assertEqual(response.status_code, 200)

    def test_check_username_availability_unavailable(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(
            reverse("users-check-availability", kwargs={"username": "testuser"})
        )
        self.assertEqual(response.status_code, 409)

    # Testcases for getting current user details

    def test_get_current_user_details(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("users-getcurrentuser"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], self.user.username)

    # Testcases for user pnconfig

    def test_get_pnconfig(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse("users-pnconfig", kwargs={"username": self.user.username})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["pf_endpoint"], self.user.pf_endpoint)
        self.assertEqual(response.data["pf_p256dh"], self.user.pf_p256dh)
        self.assertEqual(response.data["pf_auth"], self.user.pf_auth)

    def test_update_pnconfig(self):
        self.client.force_authenticate(user=self.user)
        update_data = {
            "pf_endpoint": "https://example.com/endpoint",
            "pf_p256dh": "p256dh_key",
            "pf_auth": "auth_key",
        }
        response = self.client.patch(
            reverse("users-pnconfig", kwargs={"username": self.user.username}),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.pf_endpoint, update_data["pf_endpoint"])
        self.assertEqual(self.user.pf_p256dh, update_data["pf_p256dh"])
        self.assertEqual(self.user.pf_auth, update_data["pf_auth"])

    # Testcases for searching user details

    def test_search_user_by_username(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(self.url, {"search_text": "testuser"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["username"], "testuser")

    def test_search_user_by_first_name(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(self.url, {"search_text": "Test"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["first_name"], "Test")

    def test_search_user_by_last_name(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(self.url, {"search_text": "User"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["last_name"], "User")


class UserProfilePictureTestCase(CareAPITestBase):
    """Test cases for user profile picture upload and deletion"""

    def setUp(self):
        super().setUp()
        self.super_user = self.create_super_user(
            username="superuser", first_name="Super", last_name="User"
        )
        self.organization = self.create_organization(
            user=self.super_user, name="Parent Organization", org_type="govt"
        )
        self.user = self.create_user(
            username="testuser",
            first_name="Test",
            last_name="User",
            email="user@example.com",
            user_type=UserTypeOptions.administrator,
            geo_organization=self.organization,
            gender=GenderChoices.non_binary,
            phone_number="1234432100",
        )

        self.administrator_role = self.create_role_with_permissions(
            permissions=[
                UserPermissions.can_create_user.name,
                UserPermissions.can_list_user.name,
            ],
        )
        for user_type in UserTypeOptions:
            role_name = UserTypeRoleMapping[user_type.value].value.name
            self.create_role(
                name=role_name,
                is_system=True,
            )
        self.url = reverse(
            "users-profile-picture", kwargs={"username": self.user.username}
        )

    def generate_image(self, width, height, color, quality):
        image_io = BytesIO()
        image = Image.new("RGB", (width, height), color=color)
        image.save(image_io, format="JPEG", quality=quality)
        image_io.seek(0)
        return SimpleUploadedFile(
            "test_image.jpg", image_io.getvalue(), content_type="image/jpeg"
        )

    # Test cases for profile picture upload

    def test_upload_profile_picture(self):
        """Test successful upload of a profile picture"""
        # Create a larger image that meets the minimum requirements
        image_file = self.generate_image(500, 500, "red", 95)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url, {"profile_picture": image_file}, format="multipart"
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.profile_picture_url)

    def test_upload_invalid_file_format(self):
        """Test uploading a file with an unsupported format"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url,
            {"profile_picture": SimpleUploadedFile("test_file.txt", b"test content")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Upload a valid image. The file you uploaded was either not an image or a corrupted image.",
            status_code=400,
        )

    def test_upload_profile_picture_too_small_in_height(self):
        """Test uploading a profile picture that is too small in height"""
        image_file = self.generate_image(500, 100, "red", 95)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url, {"profile_picture": image_file}, format="multipart"
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Image height is less than the minimum allowed height of 400 pixels",
            status_code=400,
        )

    def test_upload_profile_picture_too_small_in_width(self):
        """Test uploading a profile picture that is too small in width"""
        image_file = self.generate_image(100, 500, "red", 95)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url, {"profile_picture": image_file}, format="multipart"
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Image width is less than the minimum allowed width of 400 pixels",
            status_code=400,
        )

    def test_upload_profile_picture_too_small_in_file_size(self):
        """Test uploading a profile picture that is too small in file size"""
        # Creating a very small image with low quality and dimensions
        image_file = self.generate_image(100, 100, "black", 1)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url, {"profile_picture": image_file}, format="multipart"
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Image size is less than the minimum allowed size of 1 KB.",
            status_code=400,
        )

    def test_upload_profile_picture_without_authentication(self):
        """Test uploading a profile picture without authentication"""
        image_file = self.generate_image(500, 500, "red", 95)
        response = self.client.post(
            self.url, {"profile_picture": image_file}, format="multipart"
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Authentication credentials were not provided.", status_code=403
        )

    # Test cases for deleting profile picture

    def test_delete_existing_profile_picture(self):
        """Test successful deletion of a profile picture"""
        # First, upload a profile picture
        image_file = self.generate_image(500, 500, "red", 95)
        self.client.force_authenticate(user=self.user)
        self.client.post(self.url, {"profile_picture": image_file}, format="multipart")
        # Now delete the profile picture
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(self.user.profile_picture_url)

    def test_delete_profile_picture_without_authentication(self):
        """Test deleting a profile picture without authentication"""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Authentication credentials were not provided.", status_code=403
        )

    def test_delete_profile_picture_without_existing_picture(self):
        """Test deleting a profile picture when no picture exists"""
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "No cover image to delete", status_code=404)

    def test_delete_profile_picture_as_other_user(self):
        """Test that a user cannot delete another user's profile picture"""
        other_user = self.create_user(username="otheruser")
        self.client.force_authenticate(user=other_user)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "You do not have permission to update this user", status_code=403
        )

    def test_delete_profile_picture_as_super_user(self):
        """Test that a super user can delete any user's profile picture"""
        # First, upload a profile picture
        image_file = self.generate_image(500, 500, "red", 95)
        self.client.force_authenticate(user=self.user)
        self.client.post(self.url, {"profile_picture": image_file}, format="multipart")
        # Now delete the profile picture as super user
        self.client.force_authenticate(user=self.super_user)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 204)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.profile_picture_url)

    def test_delete_profile_picture_with_invalid_method(self):
        """Test that DELETE method is the only allowed method for deleting profile picture"""
        image_file = self.generate_image(500, 500, "red", 95)
        self.client.force_authenticate(user=self.user)
        self.client.post(self.url, {"profile_picture": image_file}, format="multipart")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertContains(response, 'Method \\"GET\\" not allowed', status_code=405)

    def test_profile_picture_file_is_removed_from_storage(self):
        """Test that the image file is actually removed from storage when profile picture is deleted"""
        image_file = self.generate_image(500, 500, "red", 95)
        self.client.force_authenticate(user=self.user)
        with patch(
            "care.emr.api.viewsets.user.delete_cover_image"
        ) as mock_delete_cover_image:
            response = self.client.post(
                self.url, {"profile_picture": image_file}, format="multipart"
            )
            self.assertEqual(response.status_code, 200)
            self.user.refresh_from_db()
            self.assertIsNotNone(self.user.profile_picture_url)

            file_path = self.user.profile_picture_url

            response = self.client.delete(self.url)
            self.assertEqual(response.status_code, 204)

            mock_delete_cover_image.assert_called_once_with(file_path, "avatars")

            self.user.refresh_from_db()
            self.assertIsNone(self.user.profile_picture_url)
