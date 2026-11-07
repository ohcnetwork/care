from django.urls import reverse

from care.users.models import UserFlag
from care.utils.registries.feature_flag import FlagRegistry, FlagType
from care.utils.tests.base import CareAPITestBase


class UserFlagAPITestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        # Register test flags
        FlagRegistry.register(FlagType.USER, "TEST_FLAG")
        FlagRegistry.register(FlagType.USER, "TEST_FLAG_2")
        FlagRegistry.register(FlagType.USER, "BETA_FEATURES")

        self.superuser = self.create_super_user(username="superuser")
        self.normal_user = self.create_user(username="normaluser")
        self.target_user = self.create_user(username="targetuser")

        self.base_url = reverse("user-flags-list")

    def get_detail_url(self, external_id):
        return reverse("user-flags-detail", kwargs={"external_id": external_id})

    # ========== List Tests ==========

    def test_list_user_flags_as_superuser(self):
        """Test that superuser can list all user flags"""
        self.create_user_flag(user=self.target_user, flag="TEST_FLAG")
        self.create_user_flag(user=self.normal_user, flag="TEST_FLAG_2")

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)

    def test_list_user_flags_as_normal_user(self):
        """Test that normal user cannot list user flags"""
        self.create_user_flag(user=self.target_user, flag="TEST_FLAG")

        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)

    def test_list_user_flags_unauthenticated(self):
        """Test that unauthenticated user cannot list user flags"""
        response = self.client.get(self.base_url)
        # get_queryset authorization check happens before authentication check
        self.assertEqual(response.status_code, 403)

    def test_filter_user_flags_by_user(self):
        """Test filtering user flags by user"""
        self.create_user_flag(user=self.target_user, flag="TEST_FLAG")
        self.create_user_flag(user=self.target_user, flag="TEST_FLAG_2")
        self.create_user_flag(user=self.normal_user, flag="BETA_FEATURES")

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            f"{self.base_url}?user={self.target_user.external_id}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)

    def test_filter_user_flags_by_flag_name(self):
        """Test filtering user flags by flag name (case-insensitive)"""
        self.create_user_flag(user=self.target_user, flag="TEST_FLAG")
        self.create_user_flag(user=self.normal_user, flag="TEST_FLAG_2")

        self.client.force_authenticate(user=self.superuser)

        # Test exact case
        response = self.client.get(f"{self.base_url}?flag=TEST_FLAG")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

        # Test case-insensitive
        response = self.client.get(f"{self.base_url}?flag=test_flag")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    # ========== Create Tests ==========

    def test_create_user_flag_as_superuser(self):
        """Test that superuser can create user flags"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url,
            {"flag": "TEST_FLAG", "user": self.target_user.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["flag"], "TEST_FLAG")

        # Verify flag was created and registered
        self.assertTrue(
            UserFlag.objects.filter(
                user=self.target_user, flag="TEST_FLAG", deleted=False
            ).exists()
        )

    def test_create_user_flag_as_normal_user(self):
        """Test that normal user cannot create user flags"""
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.post(
            self.base_url,
            {"flag": "TEST_FLAG", "user": self.target_user.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_create_user_flag_with_invalid_user_uuid(self):
        """Test that creating user flag with invalid user UUID fails"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url,
            {"flag": "TEST_FLAG", "user": "00000000-0000-0000-0000-000000000000"},
            format="json",
        )
        # Invalid UUID causes validation error (400), not 404
        self.assertEqual(response.status_code, 400)

    def test_create_user_flag_missing_required_fields(self):
        """Test that creating user flag without required fields fails"""
        self.client.force_authenticate(user=self.superuser)

        # Missing flag
        response = self.client.post(
            self.base_url,
            {"user": self.target_user.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

        # Missing user
        response = self.client.post(
            self.base_url,
            {"flag": "TEST_FLAG"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    # ========== Retrieve Tests ==========

    def test_retrieve_user_flag_as_superuser(self):
        """Test that superuser can retrieve user flag"""
        flag = self.create_user_flag(user=self.target_user, flag="TEST_FLAG")

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_detail_url(flag.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["flag"], "TEST_FLAG")
        self.assertIn("user", response.data)

    def test_retrieve_user_flag_as_normal_user(self):
        """Test that normal user cannot retrieve user flag (queryset filtered)"""
        flag = self.create_user_flag(user=self.target_user, flag="TEST_FLAG")

        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get(self.get_detail_url(flag.external_id))
        # get_queryset blocks access, returns 403
        self.assertEqual(response.status_code, 403)

    def test_retrieve_non_existent_user_flag(self):
        """Test that retrieving non-existent user flag returns 404"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.get_detail_url("00000000-0000-0000-0000-000000000000")
        )
        self.assertEqual(response.status_code, 404)

    def test_retrieve_deleted_user_flag(self):
        """Test that retrieving deleted user flag returns 404"""
        flag = self.create_user_flag(user=self.target_user, flag="TEST_FLAG")
        flag.deleted = True
        flag.save()

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_detail_url(flag.external_id))
        self.assertEqual(response.status_code, 404)

    # ========== Update Tests ==========

    def test_update_user_flag_as_superuser(self):
        """Test that superuser can update user flag"""
        flag = self.create_user_flag(user=self.target_user, flag="TEST_FLAG")

        self.client.force_authenticate(user=self.superuser)
        response = self.client.put(
            self.get_detail_url(flag.external_id),
            {"flag": "TEST_FLAG_2"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["flag"], "TEST_FLAG_2")

        # Verify in database
        flag.refresh_from_db()
        self.assertEqual(flag.flag, "TEST_FLAG_2")

    def test_update_user_flag_as_normal_user(self):
        """Test that normal user cannot update user flag"""
        flag = self.create_user_flag(user=self.target_user, flag="TEST_FLAG")

        self.client.force_authenticate(user=self.normal_user)
        response = self.client.put(
            self.get_detail_url(flag.external_id),
            {"flag": "TEST_FLAG_2"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_partial_update_user_flag(self):
        """Test that partial update (PATCH) works"""
        flag = self.create_user_flag(user=self.target_user, flag="TEST_FLAG")

        self.client.force_authenticate(user=self.superuser)
        response = self.client.patch(
            self.get_detail_url(flag.external_id),
            {"flag": "BETA_FEATURES"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["flag"], "BETA_FEATURES")

    # ========== Delete Tests ==========

    def test_delete_user_flag_as_superuser(self):
        """Test that superuser can delete user flag"""
        flag = self.create_user_flag(user=self.target_user, flag="TEST_FLAG")

        self.client.force_authenticate(user=self.superuser)
        response = self.client.delete(self.get_detail_url(flag.external_id))
        self.assertEqual(response.status_code, 204)

        # Verify soft delete
        flag.refresh_from_db()
        self.assertTrue(flag.deleted)

    def test_delete_user_flag_as_normal_user(self):
        """Test that normal user cannot delete user flag"""
        flag = self.create_user_flag(user=self.target_user, flag="TEST_FLAG")

        self.client.force_authenticate(user=self.normal_user)
        response = self.client.delete(self.get_detail_url(flag.external_id))
        self.assertEqual(response.status_code, 403)

    def test_delete_already_deleted_user_flag(self):
        """Test that deleting already deleted flag returns 404"""
        flag = self.create_user_flag(user=self.target_user, flag="TEST_FLAG")
        flag.deleted = True
        flag.save()

        self.client.force_authenticate(user=self.superuser)
        response = self.client.delete(self.get_detail_url(flag.external_id))
        self.assertEqual(response.status_code, 404)

    def test_delete_unregisters_flag(self):
        """Test that deleting flag unregisters it from registry"""
        # Create a unique flag
        unique_flag = "UNIQUE_TEST_FLAG_DELETE"
        FlagRegistry.register(FlagType.USER, unique_flag)
        flag = self.create_user_flag(user=self.target_user, flag=unique_flag)

        self.client.force_authenticate(user=self.superuser)
        response = self.client.delete(self.get_detail_url(flag.external_id))
        self.assertEqual(response.status_code, 204)

        # Verify flag is unregistered
        flags = FlagRegistry.get_all_flags(FlagType.USER)
        self.assertNotIn(unique_flag, flags)

    # ========== Available Flags Tests ==========

    def test_available_flags_as_superuser(self):
        """Test that superuser can view available flags"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(f"{self.base_url}available-flags/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("available_flags", response.data)
        self.assertIn("TEST_FLAG", response.data["available_flags"])
        self.assertIn("TEST_FLAG_2", response.data["available_flags"])

    def test_available_flags_as_normal_user(self):
        """Test that normal user cannot view available flags"""
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get(f"{self.base_url}available-flags/")
        self.assertEqual(response.status_code, 403)

    # ========== Helper Methods ==========

    def create_user_flag(self, user, flag):
        # Register flag (idempotent operation, safe to call multiple times)
        FlagRegistry.register(FlagType.USER, flag)
        return UserFlag.objects.create(user=user, flag=flag)

    # ========== Multi-User Flag Deletion Tests ==========

    def test_delete_flag_does_not_unregister_when_other_users_have_it(self):
        """Test that deleting flag from one user doesn't unregister if other users have it"""
        # Create same flag for two users
        flag1 = self.create_user_flag(user=self.target_user, flag="SHARED_FLAG")
        flag2 = self.create_user_flag(user=self.normal_user, flag="SHARED_FLAG")

        self.client.force_authenticate(user=self.superuser)

        # Delete flag from first user
        response = self.client.delete(self.get_detail_url(flag1.external_id))
        self.assertEqual(response.status_code, 204)

        # Verify flag is still registered (because normal_user still has it)
        flags = FlagRegistry.get_all_flags(FlagType.USER)
        self.assertIn("SHARED_FLAG", flags)

        # Verify second user's flag still works
        flag2.refresh_from_db()
        self.assertEqual(flag2.flag, "SHARED_FLAG")
        self.assertFalse(flag2.deleted)

    def test_delete_last_user_with_flag_unregisters_it(self):
        """Test that deleting the last user with a flag unregisters it"""
        # Create flag for only one user
        flag = self.create_user_flag(user=self.target_user, flag="UNIQUE_USER_FLAG")

        self.client.force_authenticate(user=self.superuser)

        # Delete the only instance
        response = self.client.delete(self.get_detail_url(flag.external_id))
        self.assertEqual(response.status_code, 204)

        # Verify flag is unregistered (no other users have it)
        flags = FlagRegistry.get_all_flags(FlagType.USER)
        self.assertNotIn("UNIQUE_USER_FLAG", flags)

    def test_delete_multiple_users_with_same_flag_sequence(self):
        """Test deleting flag from multiple users in sequence"""
        # Create same flag for three users
        superuser_flag = self.create_user_flag(
            user=self.superuser, flag="MULTI_USER_FLAG"
        )
        target_flag = self.create_user_flag(
            user=self.target_user, flag="MULTI_USER_FLAG"
        )
        normal_flag = self.create_user_flag(
            user=self.normal_user, flag="MULTI_USER_FLAG"
        )

        self.client.force_authenticate(user=self.superuser)

        # Delete first user's flag
        response = self.client.delete(self.get_detail_url(target_flag.external_id))
        self.assertEqual(response.status_code, 204)
        flags = FlagRegistry.get_all_flags(FlagType.USER)
        self.assertIn("MULTI_USER_FLAG", flags)  # Still registered

        # Delete second user's flag
        response = self.client.delete(self.get_detail_url(normal_flag.external_id))
        self.assertEqual(response.status_code, 204)
        flags = FlagRegistry.get_all_flags(FlagType.USER)
        self.assertIn("MULTI_USER_FLAG", flags)  # Still registered (superuser has it)

        # Delete last user's flag
        response = self.client.delete(self.get_detail_url(superuser_flag.external_id))
        self.assertEqual(response.status_code, 204)
        flags = FlagRegistry.get_all_flags(FlagType.USER)
        self.assertNotIn("MULTI_USER_FLAG", flags)  # Now unregistered
