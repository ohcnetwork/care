from django.urls import reverse
from model_bakery import baker

from care.emr.models.scheduling.token import TokenCategory
from care.emr.resources.scheduling.schedule.spec import SchedulableResourceTypeOptions
from care.security.permissions.token import TokenPermissions
from care.utils.tests.base import CareAPITestBase


class TokenCategoryAPITestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.superuser = self.create_super_user()
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, org_type="root"
        )
        self.patient = self.create_patient()
        self.role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token_category.name,
                TokenPermissions.can_write_token_category.name,
            ],
        )
        self.base_url = self.generate_category_url(
            facility=str(self.facility.external_id),
        )

    def generate_token_category_data(self, **kwargs):
        data = {
            "name": kwargs.get("name", "General"),
            "resource_type": kwargs.get(
                "resource_type", SchedulableResourceTypeOptions.location
            ),
            "shorthand": kwargs.get("shorthand", "GEN"),
            "metadata": kwargs.get("metadata", {"description": "General category"}),
        }
        data.update(kwargs)
        return data

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
        response = self.client.post(
            self.base_url, self.generate_token_category_data(), format="json"
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                facility=str(self.facility.external_id),
                external_id=response.data["id"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertEqual(get_response.data["name"], response.data["name"])
        self.assertEqual(get_response.data["shorthand"], response.data["shorthand"])

    def test_create_token_category_as_user_with_permissions(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        response = self.client.post(
            self.base_url, self.generate_token_category_data(), format="json"
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                facility=str(self.facility.external_id),
                external_id=response.data["id"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertEqual(get_response.data["name"], response.data["name"])
        self.assertEqual(get_response.data["shorthand"], response.data["shorthand"])

    def test_create_token_category_as_user_without_permissions(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url, self.generate_token_category_data(), format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Access Denied to Token Category", response.data["detail"])

    # Test cases for update token categories

    def test_update_token_category_as_superuser(self):
        category = self.create_token_category(facility=self.facility)
        self.client.force_authenticate(user=self.superuser)
        self.generate_token_category_data(
            name="Updated Category",
            shorthand="UPD",
            metadata={"description": "Updated description"},
            resource_type=SchedulableResourceTypeOptions.healthcare_service,
        )
        response = self.client.put(
            self.generate_detail_url(
                facility=str(self.facility.external_id),
                external_id=category.external_id,
            ),
            self.generate_token_category_data(
                name="Updated Category",
                shorthand="UPD",
                metadata={"description": "Updated description"},
                resource_type=SchedulableResourceTypeOptions.healthcare_service,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Updated Category")
        self.assertEqual(response.data["shorthand"], "UPD")

    def test_update_token_category_as_user_with_permissions(self):
        category = self.create_token_category(facility=self.facility)
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        response = self.client.put(
            self.generate_detail_url(
                facility=str(self.facility.external_id),
                external_id=category.external_id,
            ),
            self.generate_token_category_data(
                name="Updated Category",
                shorthand="UPD",
                metadata={"description": "Updated description"},
                resource_type=SchedulableResourceTypeOptions.healthcare_service,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Updated Category")
        self.assertEqual(response.data["shorthand"], "UPD")

    def test_update_token_category_as_user_without_permissions(self):
        category = self.create_token_category(facility=self.facility)
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            self.generate_detail_url(
                facility=str(self.facility.external_id),
                external_id=category.external_id,
            ),
            self.generate_token_category_data(
                name="Updated Category",
                shorthand="UPD",
                metadata={"description": "Updated description"},
                resource_type=SchedulableResourceTypeOptions.healthcare_service,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Access Denied to Token Category", response.data["detail"])

    # Test cases for retrieve token categories

    def test_retrieve_token_category_as_superuser(self):
        category = self.create_token_category(facility=self.facility)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.generate_detail_url(
                facility=str(self.facility.external_id),
                external_id=category.external_id,
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(category.external_id))
        self.assertEqual(response.data["name"], category.name)
        self.assertEqual(response.data["shorthand"], category.shorthand)

    def test_retrieve_token_category_as_user_with_permissions(self):
        category = self.create_token_category(facility=self.facility)
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        response = self.client.get(
            self.generate_detail_url(
                facility=str(self.facility.external_id),
                external_id=category.external_id,
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(category.external_id))
        self.assertEqual(response.data["name"], category.name)
        self.assertEqual(response.data["shorthand"], category.shorthand)

    def test_retrieve_token_category_as_user_without_permissions(self):
        category = self.create_token_category(facility=self.facility)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.generate_detail_url(
                facility=str(self.facility.external_id),
                external_id=category.external_id,
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Access Denied to Token Category", response.data["detail"])

    # Test cases for list token categories

    def test_list_token_categories_as_superuser(self):
        category1 = self.create_token_category(facility=self.facility)
        category2 = self.create_token_category(facility=self.facility)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        returned_ids = {item["id"] for item in response.data["results"]}
        self.assertIn(str(category1.external_id), returned_ids)
        self.assertIn(str(category2.external_id), returned_ids)

    def test_list_token_categories_as_user_with_permissions(self):
        category1 = self.create_token_category(facility=self.facility)
        category2 = self.create_token_category(facility=self.facility)
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        returned_ids = {item["id"] for item in response.data["results"]}
        self.assertIn(str(category1.external_id), returned_ids)
        self.assertIn(str(category2.external_id), returned_ids)

    def test_list_token_categories_as_user_without_permissions(self):
        self.create_token_category(facility=self.facility)
        self.create_token_category(facility=self.facility)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)
        self.assertIn("Access Denied to Token Category", response.data["detail"])

    def test_list_token_categories_with_resource_type_filter(self):
        category1 = self.create_token_category(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.location,
        )
        self.create_token_category(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            f"{self.base_url}?resource_type={SchedulableResourceTypeOptions.location.name}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(category1.external_id))

    def test_list_token_categories_with_name_filter(self):
        category1 = self.create_token_category(
            facility=self.facility, name="Vaccination"
        )
        self.create_token_category(facility=self.facility, name="General")
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(f"{self.base_url}?name=Vacci")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(category1.external_id))

    def test_list_token_categories_with_shorthand_filter(self):
        category1 = self.create_token_category(
            facility=self.facility,
            shorthand="VACC",
        )
        self.create_token_category(facility=self.facility, shorthand="GEN")
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(f"{self.base_url}?shorthand=VAC")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(category1.external_id))

    def test_list_token_categories_with_default_filter(self):
        category1 = self.create_token_category(
            facility=self.facility,
            default=True,
        )
        self.create_token_category(facility=self.facility, default=False)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(f"{self.base_url}?default=True")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(category1.external_id))

    # Test case for set_default action

    def test_set_default_token_category(self):
        category1 = self.create_token_category(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.location,
            default=False,
        )
        category2 = self.create_token_category(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.location,
            default=True,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            reverse(
                "token-category-set-default",
                kwargs={
                    "facility_external_id": str(self.facility.external_id),
                    "external_id": str(category1.external_id),
                },
            )
        )
        self.assertEqual(response.status_code, 200)
        category1.refresh_from_db()
        category2.refresh_from_db()
        self.assertTrue(category1.default)
        self.assertFalse(category2.default)
