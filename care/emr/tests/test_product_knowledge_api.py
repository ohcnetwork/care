from django.urls import reverse
from model_bakery import baker

from care.emr.resources.inventory.product_knowledge.spec import (
    ProductKnowledgeStatusOptions,
    ProductTypeOptions,
)
from care.security.permissions.product_knowledge import ProductKnowledgePermissions
from care.utils.tests.base import CareAPITestBase


class ProductKnowledgeAPITest(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="TestUser")
        self.superuser = self.create_super_user(username="SuperUser")
        self.facility = self.create_facility(name="Test Facility", user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            name="Test Facility Organization", facility=self.facility, org_type="root"
        )
        self.role = self.create_role_with_permissions(
            permissions=[
                ProductKnowledgePermissions.can_read_product_knowledge.name,
                ProductKnowledgePermissions.can_write_product_knowledge.name,
            ]
        )

    def generate_product_knowledge_data(
        self,
        slug=None,
        name=None,
        status=None,
        alternate_identifier=None,
        facility=None,
        product_type=None,
    ):
        return {
            "slug": slug or "test-product-knowledge",
            "alternate_identifier": alternate_identifier or "test-alternate-identifier",
            "name": name or "Test Product Knowledge",
            "status": status or ProductKnowledgeStatusOptions.active.value,
            "product_type": product_type or ProductTypeOptions.medication.value,
            "code": None,
            "base_unit": None,
            "facility": facility,
        }

    def create_product_knowledge(self, facility, **kwargs):
        data = self.generate_product_knowledge_data(facility=facility, **kwargs)
        return baker.make(
            "emr.ProductKnowledge",
            **data,
        )

    def get_details_url(self, product_knowledge=None):
        return reverse(
            "product_knowledge-detail",
            kwargs={
                "external_id": product_knowledge,
            },
        )

    def get_base_url(self):
        return reverse("product_knowledge-list")

    def create_update_product_knowledge_data(self, slug=None):
        return {
            "slug": slug or "updated-product-knowledge",
            "name": "Updated Product Knowledge",
            "status": ProductKnowledgeStatusOptions.retired.value,
            "product_type": ProductTypeOptions.medication.value,
            "code": None,
            "base_unit": None,
        }

    # Testcases for Create Product Knowledge

    def test_create_product_knowledge_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_product_knowledge_data()
        response = self.client.post(self.get_base_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_details_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_product_knowledge_as_user(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        data = self.generate_product_knowledge_data(facility=self.facility.external_id)
        response = self.client.post(self.get_base_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_details_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_product_knowledge_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        data = self.generate_product_knowledge_data(facility=self.facility.external_id)
        response = self.client.post(self.get_base_url(), data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Cannot create product knowledge", status_code=403
        )

    def test_create_product_knowledge_as_user_with_invalid_facility(self):
        another_facility = self.create_facility(
            name="Another Facility", user=self.superuser
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_product_knowledge_data(
            facility=another_facility.external_id
        )
        response = self.client.post(self.get_base_url(), data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Cannot create product knowledge", status_code=403
        )

    def test_create_product_knowledge_as_user_in_instance_level(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        data = self.generate_product_knowledge_data(facility=None)
        response = self.client.post(self.get_base_url(), data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Cannot create product knowledge", status_code=403
        )

    def test_create_product_knowledge_as_superuser_with_instance_level(self):
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_product_knowledge_data()
        response = self.client.post(self.get_base_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_details_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    # Testcases for Retrieve Product Knowledge

    def test_retrieve_product_knowledge_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        product_knowledge = self.create_product_knowledge(facility=self.facility)
        response = self.client.get(self.get_details_url(product_knowledge.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(product_knowledge.external_id))

    def test_retrieve_product_knowledge_as_user(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        product_knowledge = self.create_product_knowledge(facility=self.facility)
        response = self.client.get(self.get_details_url(product_knowledge.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(product_knowledge.external_id))

    def test_retrieve_product_knowledge_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        product_knowledge = self.create_product_knowledge(facility=self.facility)
        response = self.client.get(self.get_details_url(product_knowledge.external_id))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Cannot read product knowledge", status_code=403)

    def test_retrieve_product_knowledge_as_user_with_invalid_facility(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        another_facility = self.create_facility(
            name="Another Facility", user=self.superuser
        )
        product_knowledge = self.create_product_knowledge(facility=another_facility)
        response = self.client.get(self.get_details_url(product_knowledge.external_id))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Cannot read product knowledge", status_code=403)

    def test_retrieve_product_knowledge_as_user_in_instance_level(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        product_knowledge = self.create_product_knowledge(facility=None)
        response = self.client.get(self.get_details_url(product_knowledge.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(product_knowledge.external_id))

    def test_retrieve_product_knowledge_as_superuser_in_instance_level(self):
        self.client.force_authenticate(user=self.superuser)
        product_knowledge = self.create_product_knowledge(facility=None)
        response = self.client.get(self.get_details_url(product_knowledge.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(product_knowledge.external_id))

    # Testcases for Update Product Knowledge

    def test_update_product_knowledge_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        product_knowledge = self.create_product_knowledge(facility=self.facility)
        updated_data = self.create_update_product_knowledge_data()
        response = self.client.patch(
            self.get_details_url(product_knowledge.external_id),
            updated_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_details_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["name"], updated_data["name"])
        self.assertEqual(get_response.data["slug"], updated_data["slug"])

    def test_update_product_knowledge_as_user(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        product_knowledge = self.create_product_knowledge(facility=self.facility)
        updated_data = self.create_update_product_knowledge_data()
        response = self.client.patch(
            self.get_details_url(product_knowledge.external_id),
            updated_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_details_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["name"], updated_data["name"])
        self.assertEqual(get_response.data["slug"], updated_data["slug"])

    def test_update_product_knowledge_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        product_knowledge = self.create_product_knowledge(facility=self.facility)
        updated_data = self.create_update_product_knowledge_data()
        response = self.client.patch(
            self.get_details_url(product_knowledge.external_id),
            updated_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Cannot update product knowledge", status_code=403
        )

    def test_update_product_knowledge_as_user_in_instance_level(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        product_knowledge = self.create_product_knowledge(facility=None)
        updated_data = self.create_update_product_knowledge_data()
        response = self.client.patch(
            self.get_details_url(product_knowledge.external_id),
            updated_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Cannot update product knowledge", status_code=403
        )

    def test_update_product_knowledge_as_superuser_in_instance_level(self):
        self.client.force_authenticate(user=self.superuser)
        product_knowledge = self.create_product_knowledge(facility=None)
        updated_data = self.create_update_product_knowledge_data()
        response = self.client.patch(
            self.get_details_url(product_knowledge.external_id),
            updated_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_details_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["name"], updated_data["name"])
        self.assertEqual(get_response.data["slug"], updated_data["slug"])

    # Testcases for List Product Knowledge

    def test_list_product_knowledge_with_facility(self):
        self.client.force_authenticate(user=self.superuser)
        product = self.create_product_knowledge(facility=self.facility)
        self.create_product_knowledge(facility=None)
        response = self.client.get(
            self.get_base_url(), {"facility": self.facility.external_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(product.external_id))

    def test_list_product_knowledge_without_facility(self):
        self.client.force_authenticate(user=self.superuser)
        product = self.create_product_knowledge(facility=None)
        response = self.client.get(self.get_base_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(product.external_id))

    def test_list_product_knowledge_as_user_with_facility(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        product = self.create_product_knowledge(facility=self.facility)
        self.create_product_knowledge(facility=None)
        response = self.client.get(
            self.get_base_url(), {"facility": self.facility.external_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(product.external_id))

    def test_list_product_knowledge_as_user_without_facility(self):
        self.client.force_authenticate(user=self.user)
        product = self.create_product_knowledge(facility=None)
        response = self.client.get(self.get_base_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(product.external_id))

    # Testcases for filtering product knowledge

    def test_filter_product_knowledge_by_name(self):
        self.client.force_authenticate(user=self.superuser)
        product = self.create_product_knowledge(
            facility=self.facility, name="Test Product"
        )
        self.create_product_knowledge(facility=self.facility, name="Another Product")
        response = self.client.get(self.get_base_url(), {"name": "Test"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(product.external_id))

    def test_filter_product_knowledge_by_facility(self):
        self.client.force_authenticate(user=self.superuser)
        product = self.create_product_knowledge(
            facility=self.facility, name="Test Product"
        )
        self.create_product_knowledge(facility=self.facility, name="Another Product")
        response = self.client.get(
            self.get_base_url(), {"facility": self.facility.external_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], str(product.external_id))

    def test_filter_product_knowledge_by_status(self):
        self.client.force_authenticate(user=self.superuser)
        product = self.create_product_knowledge(
            facility=self.facility, name="Test Product", status="active"
        )
        self.create_product_knowledge(
            facility=self.facility, name="Another Product", status="inactive"
        )
        response = self.client.get(self.get_base_url(), {"status": "active"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(product.external_id))

    def test_filter_product_knowledge_by_product_type(self):
        self.client.force_authenticate(user=self.superuser)
        product = self.create_product_knowledge(
            facility=self.facility, name="Test Product", product_type="medication"
        )
        self.create_product_knowledge(
            facility=self.facility, name="Another Product", product_type="consumable"
        )
        response = self.client.get(self.get_base_url(), {"product_type": "medication"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(product.external_id))

    def test_filter_product_knowledge_by_facility_by_null(self):
        self.client.force_authenticate(user=self.superuser)
        product = self.create_product_knowledge(
            facility=None, name="Test Product", product_type="medication"
        )
        self.create_product_knowledge(
            facility=self.facility, name="Another Product", product_type="consumable"
        )
        response = self.client.get(self.get_base_url(), {"facility_is_null": True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(product.external_id))

    def test_filter_product_knowledge_by_alternate_identifier(self):
        self.client.force_authenticate(user=self.superuser)
        product = self.create_product_knowledge(
            facility=self.facility,
            name="Test Product",
            product_type="medication",
            alternate_identifier="12345",
        )
        self.create_product_knowledge(
            facility=self.facility,
            name="Another Product",
            product_type="consumable",
            alternate_identifier="67890",
        )
        response = self.client.get(
            self.get_base_url(), {"alternate_identifier": "12345"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(product.external_id))

    # Testcases for Validation

    def test_create_product_knowledge_with_duplicate_slug(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_product_knowledge(
            facility=self.facility,
            name="Test Product",
            slug="test-duplicate-product-knowledge",
        )
        response = self.client.post(
            self.get_base_url(),
            self.generate_product_knowledge_data(
                facility=self.facility.external_id,
                name="Test Product",
                product_type="medication",
                alternate_identifier="12345",
                slug="test-duplicate-product-knowledge",
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Slug already exists.", status_code=400)

    def test_create_product_knowledge_with_duplicate_slug_in_different_facility(self):
        self.client.force_authenticate(user=self.superuser)
        another_facility = self.create_facility(
            name="Another Facility", user=self.superuser
        )
        self.create_product_knowledge(
            facility=self.facility,
            name="Test Product",
            slug="test-duplicate-product-knowledge",
        )
        response = self.client.post(
            self.get_base_url(),
            self.generate_product_knowledge_data(
                facility=another_facility.external_id,
                name="Test Product",
                product_type="medication",
                alternate_identifier="12345",
                slug="test-duplicate-product-knowledge",
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_details_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_product_knowledge_with_duplicate_slug_in_instance_level(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_product_knowledge(
            facility=None,
            name="Test Product",
            slug="test-duplicate-product-knowledge",
        )
        response = self.client.post(
            self.get_base_url(),
            self.generate_product_knowledge_data(
                facility=None,
                name="Test Product",
                product_type="medication",
                alternate_identifier="12345",
                slug="test-duplicate-product-knowledge",
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Slug already exists.", status_code=400)

    def test_create_product_knowledge_with_duplicate_slug_in_instance_and_facility_level(
        self,
    ):
        self.client.force_authenticate(user=self.superuser)
        self.create_product_knowledge(
            facility=None,
            name="Test Product",
            slug="test-duplicate-product-knowledge",
        )
        self.create_product_knowledge(
            facility=self.facility,
            name="Test Product",
            slug="test-duplicate-product-knowledge",
        )
        another_facility = self.create_facility(
            name="Another Facility", user=self.superuser
        )
        response = self.client.post(
            self.get_base_url(),
            self.generate_product_knowledge_data(
                facility=another_facility.external_id,
                name="Test Product",
                product_type="medication",
                alternate_identifier="12345",
                slug="test-duplicate-product-knowledge",
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_details_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_update_product_knowledge_with_duplicate_slug_in_facility_level(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_product_knowledge(
            facility=self.facility,
            name="Test Product",
            slug="test-duplicate-product-knowledge",
        )
        product2 = self.create_product_knowledge(
            facility=self.facility,
            name="Test Product",
            slug="test-product-knowledge",
        )
        response = self.client.put(
            self.get_details_url(product2.external_id),
            self.create_update_product_knowledge_data(
                slug="test-duplicate-product-knowledge"
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Slug already exists.", status_code=400)

    def test_update_product_knowledge_with_duplicate_slug_in_instance_level(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_product_knowledge(
            facility=None,
            name="Test Product",
            slug="test-duplicate-product-knowledge",
        )
        product2 = self.create_product_knowledge(
            facility=None,
            name="Test Product",
            slug="test-product-knowledge",
        )
        response = self.client.put(
            self.get_details_url(product2.external_id),
            self.create_update_product_knowledge_data(
                slug="test-duplicate-product-knowledge"
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_update_product_knowledge_with_duplicate_slug_in_instance_and_facility_level(
        self,
    ):
        self.client.force_authenticate(user=self.superuser)
        self.create_product_knowledge(
            facility=self.facility,
            name="Test Product",
            slug="test-duplicate-product-knowledge",
        )
        product2 = self.create_product_knowledge(
            facility=None,
            name="Test Product",
            slug="test-product-knowledge",
        )
        response = self.client.put(
            self.get_details_url(product2.external_id),
            self.create_update_product_knowledge_data(
                slug="test-duplicate-product-knowledge"
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_details_url(product2.external_id))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], str(product2.external_id))
