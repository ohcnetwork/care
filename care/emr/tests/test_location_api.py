import datetime
import uuid
from secrets import choice

from django.test import ignore_warnings, override_settings
from django.urls import reverse
from django.utils import timezone

from care.emr.models import (
    FacilityLocation,
    FacilityLocationEncounter,
    FacilityLocationOrganization,
)
from care.emr.resources.encounter.constants import (
    COMPLETED_CHOICES,
    ClassChoices,
    EncounterPriorityChoices,
)
from care.emr.resources.encounter.constants import (
    StatusChoices as EncounterStatusChoices,
)
from care.emr.resources.location.spec import (
    FacilityLocationFormChoices,
    FacilityLocationModeChoices,
    FacilityLocationOperationalStatusChoices,
    InventoryUsage,
    LocationEncounterAvailabilityStatusChoices,
    StatusChoices,
)
from care.facility.models import Facility
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.facility_organization import (
    FacilityOrganizationPermissions,
)
from care.security.permissions.location import FacilityLocationPermissions
from care.utils.tests.base import CareAPITestBase


class FacilityLocationMixin:
    """Mixin to provide common methods for facility location tests."""

    def generate_data_for_facility_location(self, **kwargs):
        data = {
            "status": choice(list(StatusChoices)).value,
            "operational_status": choice(
                list(FacilityLocationOperationalStatusChoices)
            ).value,
            "name": self.fake.name(),
            "description": self.fake.text(),
            "form": choice(list(FacilityLocationFormChoices)).value,
            "organizations": [self.facility.default_internal_organization.external_id],
            "mode": choice(list(FacilityLocationModeChoices)).value,
        }
        data.update(kwargs)
        return data

    def create_facility_location(self, **kwargs):
        """
        Create a facility location using the superuser and return the response data.
        If a 'facility' keyword is passed, use that facility's external_id.
        """
        self.client.force_authenticate(user=self.super_user)
        facility_external_id = kwargs.pop("facility", self.facility.external_id)
        url = reverse(
            "location-list", kwargs={"facility_external_id": facility_external_id}
        )
        facility = Facility.objects.get(external_id=facility_external_id)
        # Allow overriding organizations if provided; otherwise, default to the facility's internal organization.
        kwargs.setdefault(
            "organizations", [facility.default_internal_organization.external_id]
        )
        data = self.generate_data_for_facility_location(**kwargs)
        response = self.client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        self.client.force_authenticate(user=self.user)
        return response.data

    def authenticate_with_permissions(self, permissions):
        """
        Create a role with the given permissions and attach it to the current user
        for the facility's default internal organization.
        """
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(
            self.facility.default_internal_organization, self.user, role
        )


class TestFacilityLocationViewSet(FacilityLocationMixin, CareAPITestBase):
    def setUp(self):
        self.super_user = self.create_super_user()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.patient = self.create_patient()
        self.client.force_authenticate(user=self.user)
        self.base_url = reverse(
            "location-list", kwargs={"facility_external_id": self.facility.external_id}
        )

    def test_deleting_child_location_updates_parent(self):
        self.authenticate_with_permissions(
            [
                FacilityLocationPermissions.can_list_facility_locations.name,
                FacilityLocationPermissions.can_write_facility_locations.name,
            ]
        )
        parent_location = self.create_facility_location(
            mode=FacilityLocationModeChoices.kind.value
        )
        child_location_1 = self.create_facility_location(
            parent=parent_location["id"],
            mode=FacilityLocationModeChoices.instance.value,
        )
        child_location_2 = self.create_facility_location(
            parent=parent_location["id"],
            mode=FacilityLocationModeChoices.instance.value,
        )

        # Delete the first child location
        url_1 = reverse(
            "location-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": child_location_1["id"],
            },
        )
        response_1 = self.client.delete(url_1, format="json")
        self.assertEqual(response_1.status_code, 204)

        parent_location_instance = FacilityLocation.objects.get(
            external_id=parent_location["id"]
        )
        parent_location_instance.refresh_from_db()
        self.assertTrue(parent_location_instance.has_children)
        self.assertFalse(parent_location_instance.has_sub_locations)
        self.assertTrue(parent_location_instance.has_beds)

        # Delete the second child location
        url_2 = reverse(
            "location-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": child_location_2["id"],
            },
        )
        response_2 = self.client.delete(url_2, format="json")
        self.assertEqual(response_2.status_code, 204)

        parent_location_instance.refresh_from_db()
        self.assertFalse(parent_location_instance.has_children)
        self.assertFalse(parent_location_instance.has_sub_locations)
        self.assertFalse(parent_location_instance.has_beds)

    def assert_location_child_flags(self, location_id, *, sub_locations, beds):
        location = FacilityLocation.objects.get(external_id=location_id)
        self.assertEqual(location.has_sub_locations, sub_locations)
        self.assertEqual(location.has_beds, beds)
        self.assertEqual(location.has_children, sub_locations or beds)

    def test_child_flags_use_direct_child_modes(self):
        parent = self.create_facility_location(
            mode=FacilityLocationModeChoices.kind.value
        )
        self.assertFalse(parent["has_sub_locations"])
        self.assertFalse(parent["has_beds"])

        room = self.create_facility_location(
            parent=parent["id"],
            mode=FacilityLocationModeChoices.kind.value,
            form=FacilityLocationFormChoices.bd.value,
        )
        self.assertTrue(room["parent"]["has_sub_locations"])
        self.assertFalse(room["parent"]["has_beds"])
        self.assert_location_child_flags(parent["id"], sub_locations=True, beds=False)

        bed = self.create_facility_location(
            parent=room["id"],
            mode=FacilityLocationModeChoices.instance.value,
            form=FacilityLocationFormChoices.ro.value,
        )
        self.assertFalse(bed["parent"]["has_sub_locations"])
        self.assertTrue(bed["parent"]["has_beds"])
        self.assert_location_child_flags(parent["id"], sub_locations=True, beds=False)
        self.assert_location_child_flags(room["id"], sub_locations=False, beds=True)

        sibling_bed = self.create_facility_location(
            parent=parent["id"], mode=FacilityLocationModeChoices.instance.value
        )
        self.assertTrue(sibling_bed["parent"]["has_sub_locations"])
        self.assertTrue(sibling_bed["parent"]["has_beds"])
        self.assert_location_child_flags(parent["id"], sub_locations=True, beds=True)

    def test_stale_parent_save_recalculates_child_flags(self):
        parent = self.create_facility_location(
            mode=FacilityLocationModeChoices.kind.value
        )
        stale_parent = FacilityLocation.objects.get(external_id=parent["id"])
        child = self.create_facility_location(
            parent=parent["id"], mode=FacilityLocationModeChoices.instance.value
        )
        stale_parent.description = "Updated after child creation"
        stale_parent.save()
        self.assert_location_child_flags(parent["id"], sub_locations=False, beds=True)

        FacilityLocation.objects.get(external_id=child["id"]).delete()
        stale_parent.description = "Updated after child deletion"
        stale_parent.save()
        self.assert_location_child_flags(parent["id"], sub_locations=False, beds=False)

    def test_child_flags_are_read_only_and_in_list_and_retrieve(self):
        parent = self.create_facility_location(
            mode=FacilityLocationModeChoices.kind.value,
            has_sub_locations=True,
            has_beds=True,
        )
        self.assertFalse(parent["has_sub_locations"])
        self.assertFalse(parent["has_beds"])
        self.create_facility_location(
            parent=parent["id"], mode=FacilityLocationModeChoices.instance.value
        )
        self.client.force_authenticate(user=self.super_user)
        detail_url = f"{self.base_url}{parent['id']}/"
        response = self.client.put(
            detail_url,
            data=self.generate_data_for_facility_location(
                has_sub_locations=True, has_beds=False
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["has_sub_locations"])
        self.assertTrue(response.data["has_beds"])

        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["has_sub_locations"])
        self.assertTrue(response.data["has_beds"])

        response = self.client.get(self.base_url, data={"parent": ""})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertFalse(response.data["results"][0]["has_sub_locations"])
        self.assertTrue(response.data["results"][0]["has_beds"])

    def test_deleting_mixed_children_updates_each_flag_independently(self):
        parent = self.create_facility_location(
            mode=FacilityLocationModeChoices.kind.value
        )
        room = self.create_facility_location(
            parent=parent["id"], mode=FacilityLocationModeChoices.kind.value
        )
        bed = self.create_facility_location(
            parent=parent["id"], mode=FacilityLocationModeChoices.instance.value
        )
        self.client.force_authenticate(user=self.super_user)
        response = self.client.delete(f"{self.base_url}{room['id']}/")
        self.assertEqual(response.status_code, 204)
        self.assert_location_child_flags(parent["id"], sub_locations=False, beds=True)

        response = self.client.delete(f"{self.base_url}{bed['id']}/")
        self.assertEqual(response.status_code, 204)
        self.assert_location_child_flags(parent["id"], sub_locations=False, beds=False)

    def test_model_delete_and_restore_update_child_flags(self):
        parent = self.create_facility_location(
            mode=FacilityLocationModeChoices.kind.value
        )
        child = self.create_facility_location(
            parent=parent["id"], mode=FacilityLocationModeChoices.kind.value
        )
        child_instance = FacilityLocation.objects.get(external_id=child["id"])
        child_instance.delete()
        self.assert_location_child_flags(parent["id"], sub_locations=False, beds=False)

        child_instance.deleted = False
        child_instance.save(update_fields=["deleted"])
        self.assert_location_child_flags(parent["id"], sub_locations=True, beds=False)

    def test_model_mode_changes_update_child_flags(self):
        parent = self.create_facility_location(
            mode=FacilityLocationModeChoices.kind.value
        )
        child = self.create_facility_location(
            parent=parent["id"], mode=FacilityLocationModeChoices.kind.value
        )
        child_instance = FacilityLocation.objects.get(external_id=child["id"])
        child_instance.mode = FacilityLocationModeChoices.instance.value
        child_instance.save(update_fields=["mode"])
        self.assert_location_child_flags(parent["id"], sub_locations=False, beds=True)

    def test_sync_children_flags_can_skip_parent(self):
        parent = self.create_facility_location(
            mode=FacilityLocationModeChoices.kind.value
        )
        child = self.create_facility_location(
            parent=parent["id"], mode=FacilityLocationModeChoices.kind.value
        )
        FacilityLocation.objects.filter(external_id=child["id"]).update(
            mode=FacilityLocationModeChoices.instance.value
        )
        child_instance = FacilityLocation.objects.get(external_id=child["id"])
        child_instance.sync_children_flags(sync_parent=False)
        self.assert_location_child_flags(parent["id"], sub_locations=True, beds=False)

        child_instance.sync_children_flags()
        self.assert_location_child_flags(parent["id"], sub_locations=False, beds=True)

    def test_child_flags_ignore_unsaved_mode_changes(self):
        parent = self.create_facility_location(
            mode=FacilityLocationModeChoices.kind.value
        )
        child = self.create_facility_location(
            parent=parent["id"], mode=FacilityLocationModeChoices.kind.value
        )
        child_instance = FacilityLocation.objects.get(external_id=child["id"])
        child_instance.mode = FacilityLocationModeChoices.instance.value
        child_instance.description = "Updated description"
        child_instance.save(update_fields=["description"])
        self.assert_location_child_flags(parent["id"], sub_locations=True, beds=False)

    def test_child_changes_update_only_immediate_parent(self):
        grandparent = self.create_facility_location(
            mode=FacilityLocationModeChoices.kind.value
        )
        parent = self.create_facility_location(
            parent=grandparent["id"], mode=FacilityLocationModeChoices.kind.value
        )
        sibling = self.create_facility_location(
            parent=parent["id"], mode=FacilityLocationModeChoices.kind.value
        )
        descendant = self.create_facility_location(
            parent=sibling["id"], mode=FacilityLocationModeChoices.instance.value
        )
        unaffected_locations = FacilityLocation.objects.filter(
            external_id__in=[grandparent["id"], sibling["id"], descendant["id"]]
        ).order_by("pk")
        unchanged_fields = (
            "cached_parent_json",
            "modified_date",
            "has_children",
            "has_sub_locations",
            "has_beds",
        )
        for operation in ("mode", "delete"):
            with self.subTest(operation=operation):
                child = self.create_facility_location(
                    parent=parent["id"], mode=FacilityLocationModeChoices.instance.value
                )
                previous_values = list(unaffected_locations.values(*unchanged_fields))
                parent_instance = FacilityLocation.objects.get(external_id=parent["id"])
                parent_cache = parent_instance.cached_parent_json
                parent_modified_date = parent_instance.modified_date
                child_instance = FacilityLocation.objects.get(external_id=child["id"])
                if operation == "mode":
                    child_instance.mode = FacilityLocationModeChoices.kind.value
                    child_instance.save(update_fields=["mode"])
                else:
                    child_instance.delete()

                self.assert_location_child_flags(
                    parent["id"], sub_locations=True, beds=False
                )
                self.assertEqual(
                    list(unaffected_locations.values(*unchanged_fields)),
                    previous_values,
                )
                parent_instance.refresh_from_db()
                self.assertEqual(parent_instance.cached_parent_json, parent_cache)
                self.assertEqual(parent_instance.modified_date, parent_modified_date)

    # LIST TESTS
    def test_list_facility_locations(self):
        self.client.logout()
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)

        user = self.create_user()
        self.client.force_authenticate(user=user)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)

    def test_request_with_invalid_facility(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse("location-list", kwargs={"facility_external_id": uuid.uuid4()})
        )
        self.assertEqual(response.status_code, 404)

    # CREATE TESTS
    def test_create_facility_location_without_permission(self):
        data = self.generate_data_for_facility_location()
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"], "You do not have permission to create a location"
        )

        self.authenticate_with_permissions(
            [FacilityOrganizationPermissions.can_manage_facility_organization.name]
        )
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"], "You do not have permission to create a location"
        )

    def test_create_with_partial_permission(self):
        self.authenticate_with_permissions(
            [FacilityOrganizationPermissions.can_create_facility_organization.name]
        )
        data = self.generate_data_for_facility_location()
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "You do not have permission to given organizations",
        )

    def test_create_facility_location_with_permission(self):
        self.authenticate_with_permissions(
            [
                FacilityOrganizationPermissions.can_create_facility_organization.name,
                FacilityOrganizationPermissions.can_manage_facility_organization.name,
            ]
        )
        data = self.generate_data_for_facility_location()
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["inventory_usage"], InventoryUsage.none.value)

        data = self.generate_data_for_facility_location(organizations=[])
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_with_parent_location(self):
        self.authenticate_with_permissions(
            [FacilityOrganizationPermissions.can_manage_facility_organization.name]
        )
        # Without permission
        parent_location1 = self.create_facility_location(
            mode=FacilityLocationModeChoices.kind.value
        )
        data = self.generate_data_for_facility_location(parent=parent_location1["id"])
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 403)

        # With permission but wrong mode
        self.authenticate_with_permissions(
            [FacilityLocationPermissions.can_write_facility_locations.name]
        )
        parent_location1 = self.create_facility_location(
            mode=FacilityLocationModeChoices.instance.value
        )
        data = self.generate_data_for_facility_location(parent=parent_location1["id"])
        data["mode"] = FacilityLocationModeChoices.instance.value
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "value_error")
        self.assertIn("Instances cannot have children", error["msg"])

        # Invalid parent UUID
        data = self.generate_data_for_facility_location(parent=uuid.uuid4())
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "value_error")
        self.assertIn("Value error, Parent not found", error["msg"])

        # Different facility
        parent_location2 = self.create_facility_location(
            facility=self.create_facility(self.user).external_id,
            mode=FacilityLocationModeChoices.kind.value,
        )
        data = self.generate_data_for_facility_location(parent=parent_location2["id"])
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Parent Incompatible with Location")

    @override_settings(LOCATION_MAX_DEPTH=2)
    def test_for_maximum_depth_for_location(self):
        self.client.force_authenticate(self.super_user)

        # Create root (depth 0)
        data = self.generate_data_for_facility_location(organizations=[], mode="kind")
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        parent_id = response.data["id"]

        # Create child (depth 1)
        data = self.generate_data_for_facility_location(
            parent=parent_id, organizations=[], mode="kind"
        )
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        parent_id = response.data["id"]

        # Create child (depth 2)
        data = self.generate_data_for_facility_location(
            parent=parent_id, organizations=[], mode="kind"
        )
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        parent_id = response.data["id"]

        # Create child at depth 3 → should fail
        data = self.generate_data_for_facility_location(
            parent=parent_id, organizations=[], mode="kind"
        )
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"][0]["msg"], "Max depth reached (2)")

    @override_settings(MAX_LOCATION_IN_FACILITY=2)
    def test_for_maximum_location_in_facility(self):
        self.client.force_authenticate(self.super_user)

        data = self.generate_data_for_facility_location(organizations=[], mode="kind")
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        parent_id = response.data["id"]

        data = self.generate_data_for_facility_location(
            parent=parent_id, organizations=[], mode="kind"
        )
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        parent_id = response.data["id"]

        data = self.generate_data_for_facility_location(
            parent=parent_id, organizations=[], mode="kind"
        )
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["errors"][0]["msg"], "Max location reached for facility (2)"
        )

    def test_create_facility_location_with_invalid_sort_index(self):
        self.authenticate_with_permissions(
            [
                FacilityOrganizationPermissions.can_create_facility_organization.name,
                FacilityOrganizationPermissions.can_manage_facility_organization.name,
            ]
        )
        data = self.generate_data_for_facility_location(sort_index=-1)
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 400)
        data = self.generate_data_for_facility_location(sort_index=10001)
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_sort_index_value_setting(self):
        self.client.force_authenticate(self.super_user)

        # Step 1: Create a parent location
        data = self.generate_data_for_facility_location(mode="kind")
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        parent_id = response.data["id"]

        # Step 2: Create child 1 (sort_index = 1)
        data1 = self.generate_data_for_facility_location(parent=parent_id)
        response1 = self.client.post(self.base_url, data=data1, format="json")
        self.assertEqual(response1.status_code, 200)
        child1_id = response1.data["id"]
        self.assertEqual(response1.data["sort_index"], 1)

        # Step 3: Create child 2 (sort_index = 2)
        data2 = self.generate_data_for_facility_location(parent=parent_id)
        response2 = self.client.post(self.base_url, data=data2, format="json")
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.data["sort_index"], 2)

        # Step 4: Delete child 1
        delete_response = self.client.delete(f"{self.base_url}{child1_id}/")
        self.assertEqual(delete_response.status_code, 204)

        # Step 5: Create new child (should get sort_index = 3)
        data3 = self.generate_data_for_facility_location(parent=parent_id)
        response3 = self.client.post(self.base_url, data=data3, format="json")
        self.assertEqual(response3.status_code, 200)
        self.assertEqual(response3.data["sort_index"], 3)

    # RETRIEVE TESTS
    def test_retrieve_facility_location_without_permissions(self):
        location = self.create_facility_location()
        url = reverse(
            "location-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": location["id"],
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_retrieve_facility_location_with_permissions(self):
        self.authenticate_with_permissions(
            [FacilityLocationPermissions.can_list_facility_locations.name]
        )
        location = self.create_facility_location()
        url = reverse(
            "location-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": location["id"],
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    # UPDATE TESTS
    def test_update_facility_location_without_permissions(self):
        self.authenticate_with_permissions(
            [FacilityLocationPermissions.can_list_facility_locations.name]
        )
        location = self.create_facility_location()
        url = reverse(
            "location-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": location["id"],
            },
        )
        data = self.generate_data_for_facility_location()
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_update_facility_location_with_permissions(self):
        self.authenticate_with_permissions(
            [FacilityLocationPermissions.can_list_facility_locations.name]
        )
        location = self.create_facility_location()
        url = reverse(
            "location-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": location["id"],
            },
        )
        data = self.generate_data_for_facility_location()
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 403)

        self.authenticate_with_permissions(
            [FacilityLocationPermissions.can_write_facility_locations.name]
        )
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], data["name"])

    def test_update_inventory_usage_preserves_omitted_value_and_allows_none(self):
        self.authenticate_with_permissions(
            [
                FacilityLocationPermissions.can_list_facility_locations.name,
                FacilityLocationPermissions.can_write_facility_locations.name,
            ]
        )
        location = self.create_facility_location(
            inventory_usage=InventoryUsage.store.value
        )
        self.assertEqual(location["inventory_usage"], InventoryUsage.store.value)
        url = reverse(
            "location-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": location["id"],
            },
        )
        data = self.generate_data_for_facility_location()
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["inventory_usage"], InventoryUsage.store.value)

        data["inventory_usage"] = InventoryUsage.none.value
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["inventory_usage"], InventoryUsage.none.value)
        self.assertEqual(
            FacilityLocation.objects.get(external_id=location["id"]).inventory_usage,
            InventoryUsage.none.value,
        )

    def test_update_facility_location_with_parent(self):
        self.authenticate_with_permissions(
            [
                FacilityLocationPermissions.can_list_facility_locations.name,
                FacilityLocationPermissions.can_write_facility_locations.name,
            ]
        )
        parent = self.create_facility_location()
        location = self.create_facility_location()
        url = reverse(
            "location-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": location["id"],
            },
        )
        data = self.generate_data_for_facility_location(parent=parent["id"])
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 200)

    # DELETE TESTS
    def test_delete_facility_location_without_permissions(self):
        self.authenticate_with_permissions(
            [FacilityLocationPermissions.can_list_facility_locations.name]
        )
        location = self.create_facility_location()
        url = reverse(
            "location-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": location["id"],
            },
        )
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, 403)

    def test_delete_facility_location_with_permissions(self):
        self.authenticate_with_permissions(
            [
                FacilityLocationPermissions.can_list_facility_locations.name,
                FacilityLocationPermissions.can_write_facility_locations.name,
            ]
        )
        location = self.create_facility_location()
        url = reverse(
            "location-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": location["id"],
            },
        )
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, 204)

    def test_deleting_parent_location(self):
        self.authenticate_with_permissions(
            [
                FacilityLocationPermissions.can_list_facility_locations.name,
                FacilityLocationPermissions.can_write_facility_locations.name,
            ]
        )
        parent_location = self.create_facility_location(
            mode=FacilityLocationModeChoices.kind.value
        )
        self.create_facility_location(parent=parent_location["id"])
        url = reverse(
            "location-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": parent_location["id"],
            },
        )
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "validation_error")
        self.assertIn("Location has active children", error["msg"])

    # ORGANIZATION TESTS
    def create_facility_location_organization(self, location, organization):
        data = {"location": location, "organization": organization}
        return FacilityLocationOrganization.objects.create(**data)

    def test_retrieve_organisation_facility_location_with_permissions(self):
        self.authenticate_with_permissions(
            [FacilityLocationPermissions.can_list_facility_locations.name]
        )
        location = self.create_facility_location()
        self.create_facility_location_organization(
            FacilityLocation.objects.get(external_id=location["id"]),
            self.facility.default_internal_organization,
        )
        url = reverse(
            "location-organizations",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": location["id"],
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["results"][0]["id"],
            str(self.facility.default_internal_organization.external_id),
        )

    def test_organizations_add_to_facility_location(self):
        self.authenticate_with_permissions(
            [FacilityLocationPermissions.can_list_facility_locations.name]
        )
        location = self.create_facility_location()
        self.create_facility_location_organization(
            FacilityLocation.objects.get(external_id=location["id"]),
            self.facility.default_internal_organization,
        )
        facility_organization = self.create_facility_organization(self.facility)
        url = reverse(
            "location-organizations-add",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": location["id"],
            },
        )
        response = self.client.post(
            url, data={"organization": facility_organization.external_id}, format="json"
        )
        self.assertEqual(response.status_code, 403)

        self.authenticate_with_permissions(
            [
                FacilityLocationPermissions.can_write_facility_locations.name,
                FacilityOrganizationPermissions.can_manage_facility_organization.name,
            ]
        )
        response = self.client.post(
            url, data={"organization": facility_organization.external_id}, format="json"
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            url, data={"organization": facility_organization.external_id}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "validation_error")
        self.assertIn("Organization already exists", error["msg"])

        facility = self.create_facility(self.user)
        outside_facility_organization = self.create_facility_organization(facility)
        response = self.client.post(
            url,
            data={"organization": outside_facility_organization.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_organization_remove_to_facility_location(self):
        location = self.create_facility_location()
        self.create_facility_location_organization(
            FacilityLocation.objects.get(external_id=location["id"]),
            self.facility.default_internal_organization,
        )
        facility_organization = self.create_facility_organization(self.facility)

        self.authenticate_with_permissions(
            [FacilityLocationPermissions.can_list_facility_locations.name]
        )
        url = reverse(
            "location-organizations-remove",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": location["id"],
            },
        )
        response = self.client.post(
            url, data={"organization": facility_organization.external_id}, format="json"
        )
        self.assertEqual(response.status_code, 403)

        # Adding extra permissions
        self.authenticate_with_permissions(
            [
                FacilityLocationPermissions.can_write_facility_locations.name,
                FacilityOrganizationPermissions.can_manage_facility_organization.name,
            ]
        )
        response = self.client.post(
            url,
            data={
                "organization": self.facility.default_internal_organization.external_id
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        facility = self.create_facility(self.user)
        outside_facility_organization = self.create_facility_organization(facility)
        response = self.client.post(
            url,
            data={"organization": outside_facility_organization.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.post(
            url,
            data={"organization": self.facility_organization.external_id},
            format="json",
        )  # Organization in same facility but without a facility location created with it
        self.assertEqual(response.status_code, 400)


@ignore_warnings(category=RuntimeWarning, message=r".*received a naive datetime.*")
class TestFacilityLocationEncounterViewSet(FacilityLocationMixin, CareAPITestBase):
    def setUp(self):
        self.super_user = self.create_super_user()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.patient = self.create_patient()
        self.client.force_authenticate(user=self.user)
        self.location = self.create_facility_location(
            mode=FacilityLocationModeChoices.instance.value
        )
        self.encounter = self.create_encounter(
            self.patient, self.facility, self.facility.default_internal_organization
        )
        self.base_url = reverse(
            "association-list",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "location_external_id": self.location["id"],
            },
        )

    def generate_facility_location_encounter_data(self, encounter_id, **kwargs):
        data = {
            "status": LocationEncounterAvailabilityStatusChoices.active.value,
            "encounter": encounter_id,
            "start_datetime": timezone.now(),
            "end_datetime": None,
        }
        data.update(kwargs)
        return data

    def create_facility_location_encounter(self, encounter, **kwargs):
        data = self.generate_facility_location_encounter_data(
            encounter.external_id, **kwargs
        )
        self.client.force_authenticate(user=self.super_user)
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        self.client.force_authenticate(user=self.user)
        return response.data

    # LIST TESTS
    def test_list_without_permissions(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)

    def test_list_with_permissions(self):
        self.authenticate_with_permissions(
            [FacilityLocationPermissions.can_list_facility_locations.name]
        )
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)

    # CREATE TESTS
    def test_create_without_permissions(self):
        data = self.generate_facility_location_encounter_data(
            self.encounter.external_id
        )
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"], "You do not have permission to given location"
        )

        outside_facility_encounter = self.create_encounter(
            self.patient,
            self.create_facility(self.user),
            self.facility.default_internal_organization,
        )
        outside_data = self.generate_facility_location_encounter_data(
            outside_facility_encounter.external_id
        )
        response = self.client.post(self.base_url, data=outside_data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"], "Encounter Incompatible with Location"
        )

        self.authenticate_with_permissions(
            [FacilityLocationPermissions.can_list_facility_locations.name]
        )
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"], "You do not have permission to update encounter"
        )

        self.authenticate_with_permissions(
            [EncounterPermissions.can_write_encounter.name]
        )
        completed_encounter = self.create_encounter(
            self.patient,
            self.facility,
            self.facility.default_internal_organization,
            status=choice(COMPLETED_CHOICES),
        )
        data = self.generate_facility_location_encounter_data(
            completed_encounter.external_id
        )
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"], "You do not have permission to update encounter"
        )

    def test_create_encounter_with_valid_permissions(self):
        """Test creating a facility location encounter with the correct permissions."""
        self.authenticate_with_permissions(
            [
                FacilityLocationPermissions.can_list_facility_locations.name,
                EncounterPermissions.can_write_encounter.name,
            ]
        )
        data = self.generate_facility_location_encounter_data(
            self.encounter.external_id,
            status=LocationEncounterAvailabilityStatusChoices.active.value,
        )
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_encounter_with_conflicting_schedule(self):
        """Test creating an encounter with conflicting times should return an error."""
        self.authenticate_with_permissions(
            [
                FacilityLocationPermissions.can_list_facility_locations.name,
                EncounterPermissions.can_write_encounter.name,
            ]
        )
        data = self.generate_facility_location_encounter_data(
            self.encounter.external_id,
            status=LocationEncounterAvailabilityStatusChoices.active.value,
        )
        # First request should pass
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            FacilityLocation.objects.get(
                external_id=self.location["id"]
            ).current_encounter.id,
            self.encounter.id,
        )
        # Second request with the same time should fail
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "validation_error")
        self.assertIn("Conflict in schedule", error["msg"])

    def test_create_encounter_with_conflicting_schedule_second_case(self):
        """Test creating an encounter with conflicting times should return an error."""
        self.authenticate_with_permissions(
            [
                FacilityLocationPermissions.can_list_facility_locations.name,
                EncounterPermissions.can_write_encounter.name,
            ]
        )
        first_encounter_data = self.generate_facility_location_encounter_data(
            self.encounter.external_id,
            status=LocationEncounterAvailabilityStatusChoices.active.value,
        )
        first_encounter_data["start_datetime"] = timezone.now()
        first_encounter_data["end_datetime"] = timezone.now() + datetime.timedelta(
            hours=2
        )
        response = self.client.post(
            self.base_url, data=first_encounter_data, format="json"
        )
        self.assertEqual(response.status_code, 200)

        second_encounter_data = self.generate_facility_location_encounter_data(
            self.encounter.external_id,
            status=LocationEncounterAvailabilityStatusChoices.completed.value,
        )
        second_encounter_data["start_datetime"] = first_encounter_data[
            "start_datetime"
        ] + datetime.timedelta(hours=1)
        second_encounter_data["end_datetime"] = first_encounter_data[
            "end_datetime"
        ] + datetime.timedelta(hours=1)
        response = self.client.post(
            self.base_url, data=second_encounter_data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "validation_error")
        self.assertIn("Conflict in schedule", error["msg"])

    def test_create_encounter_when_another_active_encounter_exists(self):
        """Test creating an active encounter when another active one exists should return an error."""
        self.authenticate_with_permissions(
            [
                FacilityLocationPermissions.can_list_facility_locations.name,
                EncounterPermissions.can_write_encounter.name,
            ]
        )
        data = self.generate_facility_location_encounter_data(
            self.encounter.external_id,
            status=LocationEncounterAvailabilityStatusChoices.active.value,
        )
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 200)

        another_active_data = self.generate_facility_location_encounter_data(
            self.encounter.external_id,
            status=LocationEncounterAvailabilityStatusChoices.active.value,
        )
        response = self.client.post(
            self.base_url, data=another_active_data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "validation_error")
        self.assertIn(
            "Another active encounter already exists for this location", error["msg"]
        )

    def test_create_encounter_with_location_instance(self):
        """Test assigning an encounter to a location instance should return an error."""
        self.authenticate_with_permissions(
            [
                FacilityLocationPermissions.can_list_facility_locations.name,
                EncounterPermissions.can_write_encounter.name,
            ]
        )
        location_instance = self.create_facility_location(
            mode=FacilityLocationModeChoices.kind.value
        )
        data = self.generate_facility_location_encounter_data(
            self.encounter.external_id,
            status=LocationEncounterAvailabilityStatusChoices.active.value,
        )
        url = reverse(
            "association-list",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "location_external_id": location_instance["id"],
            },
        )
        response = self.client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "validation_error")
        self.assertIn("Cannot assign encounters to location kind", error["msg"])

    def test_create_encounter_without_end_datetime_for_completed_status(self):
        """Test that a completed encounter requires an end datetime."""
        self.authenticate_with_permissions(
            [
                FacilityLocationPermissions.can_list_facility_locations.name,
                EncounterPermissions.can_write_encounter.name,
            ]
        )
        data = self.generate_facility_location_encounter_data(
            self.encounter.external_id,
            status=LocationEncounterAvailabilityStatusChoices.completed.value,
        )
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "validation_error")
        self.assertIn("End Datetime is required for completed status", error["msg"])

    def test_create_encounter_with_invalid_end_datetime(self):
        """Test that the end datetime must be after the start datetime."""
        self.authenticate_with_permissions(
            [
                FacilityLocationPermissions.can_list_facility_locations.name,
                EncounterPermissions.can_write_encounter.name,
            ]
        )
        data = self.generate_facility_location_encounter_data(
            self.encounter.external_id,
            status=LocationEncounterAvailabilityStatusChoices.completed.value,
        )
        data["end_datetime"] = timezone.now() - datetime.timedelta(hours=2)
        response = self.client.post(self.base_url, data=data, format="json")
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "validation_error")
        self.assertIn(
            "End Datetime should be greater than Start Datetime", error["msg"]
        )

    # RETRIEVE TESTS
    def test_retrieve_without_permissions(self):
        facility_location_encounter = self.create_facility_location_encounter(
            self.encounter
        )
        url = reverse(
            "association-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "location_external_id": self.location["id"],
                "external_id": facility_location_encounter["id"],
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"], "You do not have permission to given location"
        )

    def test_retrieve_with_permissions(self):
        self.authenticate_with_permissions(
            [FacilityLocationPermissions.can_list_facility_locations.name]
        )
        facility_location_encounter = self.create_facility_location_encounter(
            self.encounter
        )
        url = reverse(
            "association-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "location_external_id": self.location["id"],
                "external_id": facility_location_encounter["id"],
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], facility_location_encounter["id"])

    def test_retrieve_facility_location_encounter_with_wrong_location(self):
        another_location = self.create_facility_location()
        facility_location_encounter = self.create_facility_location_encounter(
            self.encounter
        )
        self.client.force_authenticate(self.super_user)
        url = reverse(
            "association-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "location_external_id": another_location["id"],
                "external_id": facility_location_encounter["id"],
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["errors"][0]["msg"],
            "Location encounter does not belong to the specified location",
        )

    # DELETE TESTS
    def test_delete_without_permission(self):
        facility_location_encounter = self.create_facility_location_encounter(
            self.encounter
        )
        url = reverse(
            "association-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "location_external_id": self.location["id"],
                "external_id": facility_location_encounter["id"],
            },
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"], "You do not have permission to given location"
        )

    def test_delete_wrong_location_without_permission(self):
        another_location = self.create_facility_location()
        facility_location_encounter = self.create_facility_location_encounter(
            self.encounter
        )
        url = reverse(
            "association-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "location_external_id": another_location["id"],
                "external_id": facility_location_encounter["id"],
            },
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"], "You do not have permission to given location"
        )

    def test_delete_with_permission(self):
        self.authenticate_with_permissions(
            [
                FacilityLocationPermissions.can_list_facility_locations.name,
                EncounterPermissions.can_write_encounter.name,
            ]
        )
        facility_location_encounter = self.create_facility_location_encounter(
            self.encounter
        )
        url = reverse(
            "association-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "location_external_id": self.location["id"],
                "external_id": facility_location_encounter["id"],
            },
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            FacilityLocation.objects.filter(
                external_id=facility_location_encounter["id"]
            ).exists()
        )

    # UPDATE TESTS
    def test_update_without_permission(self):
        facility_location_encounter = self.create_facility_location_encounter(
            self.encounter
        )
        url = reverse(
            "association-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "location_external_id": self.location["id"],
                "external_id": facility_location_encounter["id"],
            },
        )
        data = self.generate_facility_location_encounter_data(
            self.encounter.external_id
        )
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"], "You do not have permission to given location"
        )

    def test_update_wrong_location_without_permission(self):
        another_location = self.create_facility_location()
        facility_location_encounter = self.create_facility_location_encounter(
            self.encounter
        )
        url = reverse(
            "association-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "location_external_id": another_location["id"],
                "external_id": facility_location_encounter["id"],
            },
        )
        data = self.generate_facility_location_encounter_data(
            self.encounter.external_id
        )
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"], "You do not have permission to given location"
        )

    def test_update_with_permission(self):
        self.authenticate_with_permissions(
            [
                FacilityLocationPermissions.can_list_facility_locations.name,
                EncounterPermissions.can_write_encounter.name,
            ]
        )
        facility_location_encounter = self.create_facility_location_encounter(
            self.encounter
        )
        url = reverse(
            "association-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "location_external_id": self.location["id"],
                "external_id": facility_location_encounter["id"],
            },
        )
        data = self.generate_facility_location_encounter_data(
            self.encounter.external_id,
            status=LocationEncounterAvailabilityStatusChoices.completed.value,
        )
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "validation_error")
        self.assertIn("End Datetime is required for completed status", error["msg"])

        data["end_datetime"] = timezone.now() + datetime.timedelta(hours=2)
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], data["status"])

        # Trying to update a completed association
        data["status"] = LocationEncounterAvailabilityStatusChoices.planned.value
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "validation_error")
        self.assertIn("Cannot change status after marking completed", error["msg"])

    def test_completion_of_location_encounter_after_encounter_status_update_to_completed(
        self,
    ):
        # Create Encounter
        encounter = self.create_encounter(
            self.patient,
            self.facility,
            self.facility.default_internal_organization,
            status_history={"history": []},
            encounter_class=ClassChoices.imp.value,
        )

        # Create Facility Location Encounter
        facility_location_encounter = self.create_facility_location_encounter(encounter)
        url = reverse(
            "association-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "location_external_id": self.location["id"],
                "external_id": facility_location_encounter["id"],
            },
        )

        data = self.generate_facility_location_encounter_data(
            encounter.external_id,
            status=LocationEncounterAvailabilityStatusChoices.active.value,
        )

        self.client.force_authenticate(self.super_user)  # To avoid permissions error
        # Update Facility Location Encounter
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        # Fetch updated object
        encounter_location_obj = FacilityLocationEncounter.objects.get(
            external_id=response.json()["id"]
        )

        # Verify status before encounter completion
        self.assertEqual(
            encounter_location_obj.status,
            LocationEncounterAvailabilityStatusChoices.active.value,
        )
        self.assertIsNone(encounter_location_obj.end_datetime)

        # Update Encounter to Completed
        encounter_update_url = reverse(
            "encounter-detail", kwargs={"external_id": encounter.external_id}
        )
        update_data = {
            "status": EncounterStatusChoices.completed.value,
            "priority": EncounterPriorityChoices.urgent.value,
            "encounter_class": ClassChoices.imp.value,
        }

        self.client.force_authenticate(self.super_user)  # To avoid permissions error
        self.client.put(encounter_update_url, data=update_data, format="json")

        # Refresh and verify encounter location status
        encounter_location_obj.refresh_from_db()
        self.assertEqual(
            encounter_location_obj.status,
            LocationEncounterAvailabilityStatusChoices.completed.value,
        )
        self.assertIsNotNone(encounter_location_obj.end_datetime)

        self.assertIsNone(
            FacilityLocation.objects.get(
                external_id=self.location["id"]
            ).current_encounter
        )
