from django.urls import reverse
from model_bakery import baker

from care.emr.models.scheduling.token import TokenCategory
from care.security.permissions.token import TokenPermissions
from care.utils.tests.base import CareAPITestBase


class TokenCategoryAPITestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.superuser = self.create_super_user()
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.patient = self.create_patient()
        self.role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token_category,
                TokenPermissions.can_write_token_category,
            ],
        )
        self.base_url = self.generate_category_url(
            facility=str(self.facility.external_id),
        )
        self.category_data = {
            "name": "General",
            "resource_type": "location",
            "shorthand": "GEN",
            "metadata": {"description": "General category"},
        }

    def generate_category_url(self, facility):
        return reverse(
            "token-category-list",
            kwargs={
                "facility_external_id": facility,
            },
        )

    def generate_detail_url(self, facility, external_id):
        return reverse(
            "token-category-detail",
            kwargs={
                "facility_external_id": facility,
                "external_id": external_id,
            },
        )

    def create_token_category(self, facility, **kwargs):
        return baker.make(
            TokenCategory,
            facility=facility,
            **kwargs,
        )

    # Test cases for create token category

    def test_create_token_category_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.base_url, self.category_data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                facility=str(self.facility.external_id),
                external_id=response.data["id"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertEqual(get_response.data["name"], self.category_data["name"])
        self.assertEqual(
            get_response.data["shorthand"], self.category_data["shorthand"]
        )

    def test_create_token_category_as_user_with_permissions(self):
        self.client.force_authenticate(user=self.user)
        self.assign_role_to_user_in_facility(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        response = self.client.post(self.base_url, self.category_data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                facility=str(self.facility.external_id),
                external_id=response.data["id"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertEqual(get_response.data["name"], self.category_data["name"])
        self.assertEqual(
            get_response.data["shorthand"], self.category_data["shorthand"]
        )

    def test_create_token_category_as_user_without_permissions(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.base_url, self.category_data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Access Denied to Token Category", response.data["detail"])
