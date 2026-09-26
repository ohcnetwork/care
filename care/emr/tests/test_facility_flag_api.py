from django.urls import reverse

from care.facility.models import FacilityFlag
from care.utils.registries.feature_flag import FlagRegistry, FlagType
from care.utils.tests.base import CareAPITestBase


class FacilityFlagAPITestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        # Register test flags
        FlagRegistry.register(FlagType.FACILITY, "TEST_FACILITY_FLAG")
        FlagRegistry.register(FlagType.FACILITY, "TEST_FACILITY_FLAG_2")
        FlagRegistry.register(FlagType.FACILITY, "ENABLE_FEATURE_X")

        self.superuser = self.create_super_user(username="superuser")
        self.normal_user = self.create_user(username="normaluser")

        self.facility = self.create_facility(name="Test Facility", user=self.superuser)
        self.facility_2 = self.create_facility(
            name="Test Facility 2", user=self.superuser
        )

        self.base_url = reverse("facility-flags-list")

    def get_detail_url(self, external_id):
        return reverse("facility-flags-detail", kwargs={"external_id": external_id})

    # ========== List Tests ==========

    def test_list_facility_flags_as_superuser(self):
        """Test that superuser can list all facility flags"""
        self.create_facility_flag(facility=self.facility, flag="TEST_FACILITY_FLAG")
        self.create_facility_flag(facility=self.facility_2, flag="TEST_FACILITY_FLAG_2")

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)

    def test_list_facility_flags_filtered_by_facility(self):
        """Test that superuser can filter facility flags by facility"""
        self.create_facility_flag(facility=self.facility, flag="TEST_FACILITY_FLAG")
        self.create_facility_flag(facility=self.facility_2, flag="TEST_FACILITY_FLAG_2")

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            f"{self.base_url}?facility={self.facility.external_id}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["flag"], "TEST_FACILITY_FLAG")

    def test_list_facility_flags_as_normal_user(self):
        """Test that normal user cannot list facility flags"""
        self.create_facility_flag(facility=self.facility, flag="TEST_FACILITY_FLAG")

        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)

    def test_list_facility_flags_unauthenticated(self):
        """Test that unauthenticated user cannot list facility flags"""
        response = self.client.get(self.base_url)
        # get_queryset authorization check happens before authentication check
        self.assertEqual(response.status_code, 403)

    def test_filter_facility_flags_by_flag_name(self):
        """Test filtering facility flags by flag name (case-insensitive)"""
        self.create_facility_flag(facility=self.facility, flag="TEST_FACILITY_FLAG")
        self.create_facility_flag(facility=self.facility_2, flag="TEST_FACILITY_FLAG_2")

        self.client.force_authenticate(user=self.superuser)

        # Test exact case
        response = self.client.get(f"{self.base_url}?flag=TEST_FACILITY_FLAG")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

        # Test case-insensitive
        response = self.client.get(f"{self.base_url}?flag=test_facility_flag")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_list_multiple_flags_same_facility(self):
        """Test listing multiple flags for the same facility"""
        self.create_facility_flag(facility=self.facility, flag="TEST_FACILITY_FLAG")
        self.create_facility_flag(facility=self.facility, flag="TEST_FACILITY_FLAG_2")

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            f"{self.base_url}?facility={self.facility.external_id}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)

    # ========== Create Tests ==========

    def test_create_facility_flag_as_superuser(self):
        """Test that superuser can create facility flag"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url,
            {
                "flag": "TEST_FACILITY_FLAG",
                "facility": self.facility.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["flag"], "TEST_FACILITY_FLAG")

        # Verify flag was created
        self.assertTrue(
            FacilityFlag.objects.filter(
                facility=self.facility, flag="TEST_FACILITY_FLAG", deleted=False
            ).exists()
        )

    def test_create_facility_flag_as_normal_user(self):
        """Test that normal user cannot create facility flag"""
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.post(
            self.base_url,
            {
                "flag": "TEST_FACILITY_FLAG",
                "facility": self.facility.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_create_facility_flag_with_invalid_facility_uuid(self):
        """Test that creating facility flag with invalid facility UUID fails"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url,
            {
                "flag": "TEST_FACILITY_FLAG",
                "facility": "00000000-0000-0000-0000-000000000000",
            },
            format="json",
        )
        # Invalid UUID causes validation error (400), not 404
        self.assertEqual(response.status_code, 400)

    def test_create_facility_flag_missing_required_fields(self):
        """Test that creating facility flag without required fields fails"""
        self.client.force_authenticate(user=self.superuser)

        # Missing flag
        response = self.client.post(
            self.base_url,
            {"facility": self.facility.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

        # Missing facility
        response = self.client.post(
            self.base_url,
            {"flag": "TEST_FACILITY_FLAG"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_same_flag_different_facilities(self):
        """Test that same flag can be created for different facilities"""
        self.client.force_authenticate(user=self.superuser)

        # Create flag for facility 1
        response1 = self.client.post(
            self.base_url,
            {
                "flag": "ENABLE_FEATURE_X",
                "facility": self.facility.external_id,
            },
            format="json",
        )
        self.assertEqual(response1.status_code, 200)

        # Create same flag for facility 2 - should succeed
        response2 = self.client.post(
            self.base_url,
            {
                "flag": "ENABLE_FEATURE_X",
                "facility": self.facility_2.external_id,
            },
            format="json",
        )
        self.assertEqual(response2.status_code, 200)

    # ========== Retrieve Tests ==========

    def test_retrieve_facility_flag_as_superuser(self):
        """Test that superuser can retrieve facility flag"""
        flag = self.create_facility_flag(
            facility=self.facility, flag="TEST_FACILITY_FLAG"
        )

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_detail_url(flag.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["flag"], "TEST_FACILITY_FLAG")
        self.assertIn("facility", response.data)

    def test_retrieve_facility_flag_as_normal_user(self):
        """Test that normal user cannot retrieve facility flag (queryset filtered)"""
        flag = self.create_facility_flag(
            facility=self.facility, flag="TEST_FACILITY_FLAG"
        )

        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get(self.get_detail_url(flag.external_id))
        # get_queryset blocks access, returns 403
        self.assertEqual(response.status_code, 403)

    def test_retrieve_non_existent_facility_flag(self):
        """Test that retrieving non-existent facility flag returns 404"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.get_detail_url("00000000-0000-0000-0000-000000000000")
        )
        self.assertEqual(response.status_code, 404)

    def test_retrieve_deleted_facility_flag(self):
        """Test that retrieving deleted facility flag returns 404"""
        flag = self.create_facility_flag(
            facility=self.facility, flag="TEST_FACILITY_FLAG"
        )
        flag.deleted = True
        flag.save()

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_detail_url(flag.external_id))
        self.assertEqual(response.status_code, 404)

    # ========== Update Tests ==========

    def test_update_facility_flag_as_superuser(self):
        """Test that superuser can update facility flag"""
        flag = self.create_facility_flag(
            facility=self.facility, flag="TEST_FACILITY_FLAG"
        )

        self.client.force_authenticate(user=self.superuser)
        response = self.client.put(
            self.get_detail_url(flag.external_id),
            {"flag": "TEST_FACILITY_FLAG_2"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["flag"], "TEST_FACILITY_FLAG_2")

        # Verify in database
        flag.refresh_from_db()
        self.assertEqual(flag.flag, "TEST_FACILITY_FLAG_2")

    def test_update_facility_flag_as_normal_user(self):
        """Test that normal user cannot update facility flag"""
        flag = self.create_facility_flag(
            facility=self.facility, flag="TEST_FACILITY_FLAG"
        )

        self.client.force_authenticate(user=self.normal_user)
        response = self.client.put(
            self.get_detail_url(flag.external_id),
            {"flag": "TEST_FACILITY_FLAG_2"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_partial_update_facility_flag(self):
        """Test that partial update (PATCH) works"""
        flag = self.create_facility_flag(
            facility=self.facility, flag="TEST_FACILITY_FLAG"
        )

        self.client.force_authenticate(user=self.superuser)
        response = self.client.patch(
            self.get_detail_url(flag.external_id),
            {"flag": "ENABLE_FEATURE_X"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["flag"], "ENABLE_FEATURE_X")

    # ========== Delete Tests ==========

    def test_delete_facility_flag_as_superuser(self):
        """Test that superuser can delete facility flag"""
        flag = self.create_facility_flag(
            facility=self.facility, flag="TEST_FACILITY_FLAG"
        )

        self.client.force_authenticate(user=self.superuser)
        response = self.client.delete(self.get_detail_url(flag.external_id))
        self.assertEqual(response.status_code, 204)

        # Verify soft delete
        flag.refresh_from_db()
        self.assertTrue(flag.deleted)

    def test_delete_facility_flag_as_normal_user(self):
        """Test that normal user cannot delete facility flag"""
        flag = self.create_facility_flag(
            facility=self.facility, flag="TEST_FACILITY_FLAG"
        )

        self.client.force_authenticate(user=self.normal_user)
        response = self.client.delete(self.get_detail_url(flag.external_id))
        self.assertEqual(response.status_code, 403)

    def test_delete_already_deleted_facility_flag(self):
        """Test that deleting already deleted flag returns 404"""
        flag = self.create_facility_flag(
            facility=self.facility, flag="TEST_FACILITY_FLAG"
        )
        flag.deleted = True
        flag.save()

        self.client.force_authenticate(user=self.superuser)
        response = self.client.delete(self.get_detail_url(flag.external_id))
        self.assertEqual(response.status_code, 404)

    def test_delete_unregisters_flag(self):
        """Test that deleting flag unregisters it from registry"""
        # Create a unique flag
        unique_flag = "UNIQUE_FACILITY_FLAG_DELETE"
        FlagRegistry.register(FlagType.FACILITY, unique_flag)
        flag = self.create_facility_flag(facility=self.facility, flag=unique_flag)

        self.client.force_authenticate(user=self.superuser)
        response = self.client.delete(self.get_detail_url(flag.external_id))
        self.assertEqual(response.status_code, 204)

        # Verify flag is unregistered
        flags = FlagRegistry.get_all_flags(FlagType.FACILITY)
        self.assertNotIn(unique_flag, flags)

    # ========== Available Flags Tests ==========

    def test_available_flags_as_superuser(self):
        """Test that superuser can view available flags"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(f"{self.base_url}available-flags/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("available_flags", response.data)
        self.assertIn("TEST_FACILITY_FLAG", response.data["available_flags"])
        self.assertIn("TEST_FACILITY_FLAG_2", response.data["available_flags"])

    def test_available_flags_as_normal_user(self):
        """Test that normal user cannot view available flags"""
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get(f"{self.base_url}available-flags/")
        self.assertEqual(response.status_code, 403)

    # ========== Helper Methods ==========

    def create_facility_flag(self, facility, flag):
        # Register flag (idempotent operation, safe to call multiple times)
        FlagRegistry.register(FlagType.FACILITY, flag)
        return FacilityFlag.objects.create(facility=facility, flag=flag)

    # ========== Multi-Facility Flag Deletion Tests ==========

    def test_delete_flag_does_not_unregister_when_other_facilities_have_it(self):
        """Test that deleting flag from one facility doesn't unregister if other facilities have it"""
        # Create same flag for two facilities
        flag1 = self.create_facility_flag(
            facility=self.facility, flag="SHARED_FACILITY_FLAG"
        )
        flag2 = self.create_facility_flag(
            facility=self.facility_2, flag="SHARED_FACILITY_FLAG"
        )

        self.client.force_authenticate(user=self.superuser)

        # Delete flag from first facility
        response = self.client.delete(self.get_detail_url(flag1.external_id))
        self.assertEqual(response.status_code, 204)

        # Verify flag is still registered (because facility_2 still has it)
        flags = FlagRegistry.get_all_flags(FlagType.FACILITY)
        self.assertIn("SHARED_FACILITY_FLAG", flags)

        # Verify second facility's flag still works
        flag2.refresh_from_db()
        self.assertEqual(flag2.flag, "SHARED_FACILITY_FLAG")
        self.assertFalse(flag2.deleted)

    def test_delete_last_facility_with_flag_unregisters_it(self):
        """Test that deleting the last facility with a flag unregisters it"""
        # Create flag for only one facility
        flag = self.create_facility_flag(
            facility=self.facility, flag="UNIQUE_FACILITY_FLAG"
        )

        self.client.force_authenticate(user=self.superuser)

        # Delete the only instance
        response = self.client.delete(self.get_detail_url(flag.external_id))
        self.assertEqual(response.status_code, 204)

        # Verify flag is unregistered (no other facilities have it)
        flags = FlagRegistry.get_all_flags(FlagType.FACILITY)
        self.assertNotIn("UNIQUE_FACILITY_FLAG", flags)

    def test_delete_multiple_facilities_with_same_flag_sequence(self):
        """Test deleting flag from multiple facilities in sequence"""
        # Create third facility for this test
        facility_3 = self.create_facility(name="Test Facility 3", user=self.superuser)

        # Create same flag for three facilities
        flag1 = self.create_facility_flag(
            facility=self.facility, flag="MULTI_FACILITY_FLAG"
        )
        flag2 = self.create_facility_flag(
            facility=self.facility_2, flag="MULTI_FACILITY_FLAG"
        )
        flag3 = self.create_facility_flag(
            facility=facility_3, flag="MULTI_FACILITY_FLAG"
        )

        self.client.force_authenticate(user=self.superuser)

        # Delete first facility's flag
        response = self.client.delete(self.get_detail_url(flag1.external_id))
        self.assertEqual(response.status_code, 204)
        flags = FlagRegistry.get_all_flags(FlagType.FACILITY)
        self.assertIn("MULTI_FACILITY_FLAG", flags)  # Still registered

        # Delete second facility's flag
        response = self.client.delete(self.get_detail_url(flag2.external_id))
        self.assertEqual(response.status_code, 204)
        flags = FlagRegistry.get_all_flags(FlagType.FACILITY)
        self.assertIn(
            "MULTI_FACILITY_FLAG", flags
        )  # Still registered (facility_3 has it)

        # Delete last facility's flag
        response = self.client.delete(self.get_detail_url(flag3.external_id))
        self.assertEqual(response.status_code, 204)
        flags = FlagRegistry.get_all_flags(FlagType.FACILITY)
        self.assertNotIn("MULTI_FACILITY_FLAG", flags)  # Now unregistered
