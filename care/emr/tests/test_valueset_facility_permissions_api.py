from django.core.cache import cache
from django.urls import reverse
from model_bakery import baker

from care.emr.models.valueset import ValueSet, ValueSetFacilityOrganization
from care.utils.tests.base import CareAPITestBase


class TestFacilityValueSetPermissions(CareAPITestBase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.creator = self.create_user()
        self.writer = self.create_user()
        self.facility = self.create_facility(self.creator)
        self.other_facility = self.create_facility(self.creator)
        self.root = self.create_facility_organization(self.facility, org_type="root")
        self.department = self.create_facility_organization(
            self.facility, org_type="dept", parent=self.root
        )
        self.other_department = self.create_facility_organization(
            self.other_facility, org_type="dept"
        )
        self.write_role = self.create_role_with_permissions(["can_write_valueset"])
        self.attach_role_facility_organization_user(
            self.root, self.writer, self.write_role
        )
        self.valueset = self.make_valueset(self.facility, "facility-valueset")
        self.other_valueset = self.make_valueset(
            self.other_facility, "other-facility-valueset"
        )
        self.list_url = reverse("value-set-list")
        self.client.force_authenticate(user=self.writer)

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def make_valueset(self, facility, slug):
        return baker.make(
            ValueSet,
            auth_context="facility",
            facility=facility,
            slug=slug,
            name="Facility value set",
            description="",
            status="active",
            compose={"include": []},
            created_by=self.creator,
            updated_by=self.creator,
        )

    def url(self, valueset, action="detail"):
        return reverse(
            f"value-set-{action}", kwargs={"external_id": valueset.external_id}
        )

    def create_payload(self, facility):
        return {
            "auth_context": "facility",
            "facility": str(facility.external_id),
            "slug": "new-facility-valueset",
            "name": "New facility value set",
            "description": "",
            "status": "active",
            "compose": {"include": []},
            "disable_composition": False,
            "inherited": False,
        }

    def assign_department(self, valueset, department):
        ValueSetFacilityOrganization.objects.create(
            valueset=valueset, organization=department
        )
        valueset.sync_facility_org_cache()

    def test_root_writer_can_create_an_unassigned_facility_valueset(self):
        response = self.client.post(
            self.list_url, self.create_payload(self.facility), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        detail_url = reverse(
            "value-set-detail", kwargs={"external_id": response.data["id"]}
        )
        self.assertEqual(self.client.get(detail_url).status_code, 200)

        response = self.client.post(
            self.list_url, self.create_payload(self.other_facility), format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_root_writer_can_manage_existing_sets_only_in_their_facility(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {item["id"] for item in response.data["results"]},
            {str(self.valueset.external_id)},
        )
        self.assertEqual(self.client.get(self.url(self.valueset)).status_code, 200)
        self.assertEqual(
            self.client.get(self.url(self.other_valueset)).status_code, 404
        )
        self.assertEqual(
            self.client.post(
                self.url(self.other_valueset, "set-facility-organizations"),
                {"facility_organizations": []},
                format="json",
            ).status_code,
            404,
        )

        organizations_url = self.url(self.valueset, "set-facility-organizations")
        response = self.client.post(
            organizations_url,
            {"facility_organizations": [str(self.department.external_id)]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.post(
            organizations_url,
            {"facility_organizations": [str(self.other_department.external_id)]},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.get(
            self.url(self.valueset, "get-facility-organizations")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(self.department.external_id)],
        )
        response = self.client.post(
            organizations_url, {"facility_organizations": []}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        payload = self.create_payload(self.facility)
        payload["name"] = "Updated unassigned set"
        response = self.client.put(self.url(self.valueset), payload, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["name"], "Updated unassigned set")
        self.assertEqual(self.client.delete(self.url(self.valueset)).status_code, 204)

    def test_readers_remain_department_scoped_and_cannot_administer_facility_sets(self):
        reader = self.create_user()
        read_role = self.create_role_with_permissions(["can_read_valueset"])
        self.attach_role_facility_organization_user(self.department, reader, read_role)
        self.client.force_authenticate(user=reader)
        self.assertEqual(self.client.get(self.url(self.valueset)).status_code, 404)

        self.assign_department(self.valueset, self.department)
        self.assign_department(self.other_valueset, self.other_department)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {item["id"] for item in response.data["results"]},
            {str(self.valueset.external_id)},
        )
        self.assertEqual(self.client.get(self.url(self.valueset)).status_code, 200)
        self.assertEqual(
            self.client.get(self.url(self.other_valueset)).status_code, 404
        )
        organizations_url = self.url(self.valueset, "set-facility-organizations")
        self.assertEqual(
            self.client.post(
                organizations_url, {"facility_organizations": []}, format="json"
            ).status_code,
            403,
        )

        # A write grant in a department does not confer root administration.
        self.attach_role_facility_organization_user(
            self.department, reader, self.write_role
        )
        self.assertEqual(
            self.client.post(
                organizations_url, {"facility_organizations": []}, format="json"
            ).status_code,
            403,
        )
        response = self.client.post(
            self.list_url, self.create_payload(self.facility), format="json"
        )
        self.assertEqual(response.status_code, 403)
        ValueSetFacilityOrganization.objects.filter(valueset=self.valueset).delete()
        self.valueset.sync_facility_org_cache()
        self.assertEqual(self.client.get(self.url(self.valueset)).status_code, 404)

        # Read permission at the root also requires a department assignment.
        self.attach_role_facility_organization_user(self.root, reader, read_role)
        self.assertEqual(self.client.get(self.url(self.valueset)).status_code, 404)
