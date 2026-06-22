import datetime

from django.urls import reverse
from model_bakery import baker

from care.emr.resources.inventory.product.spec import ProductStatusOptions
from care.emr.resources.inventory.product_knowledge.spec import (
    ProductKnowledgeStatusOptions,
    ProductTypeOptions,
)
from care.security.permissions.product import ProductPermissions
from care.utils.tests.base import CareAPITestBase


class ProductAPITest(CareAPITestBase):
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
                ProductPermissions.can_read_product.name,
                ProductPermissions.can_write_product.name,
            ]
        )
        self.resource_category = baker.make(
            "emr.ResourceCategory",
            facility=self.facility,
            slug=f"f-{self.facility.external_id}-test-category",
        )
        self.charge_item_definition = self.create_charge_item_definition(
            facility=self.facility, category=self.resource_category
        )
        self.product_knowledge = self.create_product_knowledge(
            facility=self.facility, category=self.resource_category
        )

    def generate_product_knowledge_data(
        self,
        name=None,
        status=None,
        alternate_identifier=None,
        facility=None,
        product_type=None,
        **kwargs,
    ):
        return {
            "alternate_identifier": alternate_identifier or "test-alternate-identifier",
            "name": name or "Test Product Knowledge",
            "status": status or ProductKnowledgeStatusOptions.active.value,
            "product_type": product_type or ProductTypeOptions.medication.value,
            "code": None,
            "base_unit": None,
            "facility": facility,
            **kwargs,
        }

    def create_product_knowledge(self, facility, **kwargs):
        data = self.generate_product_knowledge_data(facility=facility, **kwargs)
        return baker.make(
            "emr.ProductKnowledge",
            slug=f"f-{facility.external_id}-test-knowledge",
            **data,
        )

    def create_charge_item_definition(self, facility, slug=None, **kwargs):
        return baker.make(
            "emr.ChargeItemDefinition",
            facility=facility,
            slug=slug or f"f-{facility.external_id}-test-charge-item",
            **kwargs,
        )

    def get_details_url(self, product=None, facility=None):
        return reverse(
            "product-detail",
            kwargs={
                "external_id": product,
                "facility_external_id": facility,
            },
        )

    def get_base_url(self, facility):
        return reverse(
            "product-list",
            kwargs={
                "facility_external_id": facility,
            },
        )

    def product_data(self, product_knowledge, charge_item_definition, status=None):
        return {
            "status": status or ProductStatusOptions.active.value,
            "batch": {"lot_number": "12345"},
            "expiration_date": datetime.datetime.now(datetime.UTC)
            + datetime.timedelta(days=30),
            "product_knowledge": product_knowledge,
            "charge_item_definition": charge_item_definition,
        }

    def create_product(self, facility, **kwargs):
        data = self.product_data(**kwargs)
        return baker.make("emr.Product", facility=facility, **data)

    # Testcase for product creation

    def test_create_product_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)

        response = self.client.post(
            self.get_base_url(facility=self.facility.external_id),
            self.product_data(
                product_knowledge=self.product_knowledge.slug,
                charge_item_definition=self.charge_item_definition.slug,
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_details_url(
                product=response.data["id"], facility=self.facility.external_id
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_product_as_user_with_permissions(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            facility_organization=self.facility_organization,
            role=self.role,
        )

        response = self.client.post(
            self.get_base_url(facility=self.facility.external_id),
            self.product_data(
                product_knowledge=self.product_knowledge.slug,
                charge_item_definition=self.charge_item_definition.slug,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_details_url(
                product=response.data["id"], facility=self.facility.external_id
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_product_as_user_without_permissions(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.get_base_url(facility=self.facility.external_id),
            self.product_data(
                product_knowledge=self.product_knowledge.slug,
                charge_item_definition=self.charge_item_definition.slug,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Cannot write product", status_code=403)

    def test_create_product_with_invalid_charge_item(self):
        different_charge_item = self.create_charge_item_definition(
            facility=self.create_facility(name="Invalid Facility", user=self.user),
            category=self.resource_category,
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            facility_organization=self.facility_organization,
            role=self.role,
        )
        response = self.client.post(
            self.get_base_url(facility=self.facility.external_id),
            self.product_data(
                product_knowledge=self.product_knowledge.slug,
                charge_item_definition=different_charge_item.slug,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Invalid Charge Item", status_code=400)

    def test_create_product_with_invalid_product_knowledge(self):
        different_product_knowledge = self.create_product_knowledge(
            facility=self.create_facility(name="Invalid Facility", user=self.user),
            category=self.resource_category,
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            facility_organization=self.facility_organization,
            role=self.role,
        )
        response = self.client.post(
            self.get_base_url(facility=self.facility.external_id),
            self.product_data(
                product_knowledge=different_product_knowledge.slug,
                charge_item_definition=self.charge_item_definition.slug,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Invalid Product Knowledge", status_code=400)

    # Testcases for product updation

    def test_update_product_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        product = self.create_product(
            facility=self.facility,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
        )
        charge_item_definition = self.create_charge_item_definition(
            facility=self.facility,
            category=self.resource_category,
            slug=f"f-{self.facility.external_id}-charge-item-2",
        )
        response = self.client.put(
            self.get_details_url(
                product=product.external_id, facility=self.facility.external_id
            ),
            self.product_data(
                charge_item_definition=str(charge_item_definition.slug),
                product_knowledge=str(self.product_knowledge.slug),
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_details_url(
                product=product.external_id, facility=self.facility.external_id
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], str(product.external_id))
        self.assertEqual(
            get_response.data["charge_item_definition"]["id"],
            str(charge_item_definition.external_id),
        )

    def test_update_product_as_user_with_permissions(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            facility_organization=self.facility_organization,
            role=self.role,
        )
        product = self.create_product(
            facility=self.facility,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
        )
        charge_item_definition = self.create_charge_item_definition(
            facility=self.facility,
            category=self.resource_category,
            slug=f"f-{self.facility.external_id}-charge-item-2",
        )
        response = self.client.put(
            self.get_details_url(
                product=product.external_id, facility=self.facility.external_id
            ),
            self.product_data(
                charge_item_definition=str(charge_item_definition.slug),
                product_knowledge=str(self.product_knowledge.slug),
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_details_url(
                product=product.external_id, facility=self.facility.external_id
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], str(product.external_id))
        self.assertEqual(
            get_response.data["charge_item_definition"]["id"],
            str(charge_item_definition.external_id),
        )

    def test_update_product_as_user_without_permissions(self):
        self.client.force_authenticate(user=self.user)
        product = self.create_product(
            facility=self.facility,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
        )
        charge_item_definition = self.create_charge_item_definition(
            facility=self.facility,
        )
        response = self.client.put(
            self.get_details_url(
                product=product.external_id, facility=self.facility.external_id
            ),
            self.product_data(
                charge_item_definition=str(charge_item_definition.slug),
                product_knowledge=str(self.product_knowledge.slug),
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Cannot write product", status_code=403)

    def test_update_product_with_invalid_charge_item_definition(self):
        self.client.force_authenticate(user=self.superuser)
        product = self.create_product(
            facility=self.facility,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
        )
        different_charge_item = self.create_charge_item_definition(
            facility=self.create_facility(name="Invalid Facility", user=self.user)
        )
        response = self.client.put(
            self.get_details_url(
                product=product.external_id, facility=self.facility.external_id
            ),
            self.product_data(
                charge_item_definition=str(different_charge_item.slug),
                product_knowledge=str(self.product_knowledge.slug),
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Invalid Charge Item", status_code=400)

    # Testcases for retrieving products

    def test_retrieve_product_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        product = self.create_product(
            facility=self.facility,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
        )
        response = self.client.get(
            self.get_details_url(
                product=product.external_id, facility=self.facility.external_id
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(product.external_id))
        self.assertEqual(
            response.data["charge_item_definition"]["id"],
            str(self.charge_item_definition.external_id),
        )
        self.assertEqual(
            response.data["product_knowledge"]["id"],
            str(self.product_knowledge.external_id),
        )

    def test_retrieve_product_as_user_with_permission(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            facility_organization=self.facility_organization,
            role=self.role,
        )
        product = self.create_product(
            facility=self.facility,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
        )
        response = self.client.get(
            self.get_details_url(
                product=product.external_id, facility=self.facility.external_id
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(product.external_id))
        self.assertEqual(
            response.data["charge_item_definition"]["id"],
            str(self.charge_item_definition.external_id),
        )
        self.assertEqual(
            response.data["product_knowledge"]["id"],
            str(self.product_knowledge.external_id),
        )

    def test_retrieve_product_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        product = self.create_product(
            facility=self.facility,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
        )
        response = self.client.get(
            self.get_details_url(
                product=product.external_id, facility=self.facility.external_id
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Cannot list products", status_code=403)

    # Testcases for listing products

    def test_list_products_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        another_facility = self.create_facility(
            name="Another Facility", user=self.superuser
        )
        product = self.create_product(
            facility=self.facility,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
        )
        self.create_product(
            facility=another_facility,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
        )
        response = self.client.get(
            self.get_base_url(facility=self.facility.external_id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(product.external_id))

    def test_list_products_as_user_with_permission(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            facility_organization=self.facility_organization,
            role=self.role,
        )
        another_facility = self.create_facility(name="Another Facility", user=self.user)
        product = self.create_product(
            facility=self.facility,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
        )
        self.create_product(
            facility=another_facility,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
        )
        response = self.client.get(
            self.get_base_url(facility=self.facility.external_id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(product.external_id))

    def test_list_products_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        another_facility = self.create_facility(name="Another Facility", user=self.user)
        self.create_product(
            facility=self.facility,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
        )
        self.create_product(
            facility=another_facility,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
        )
        response = self.client.get(
            self.get_base_url(facility=self.facility.external_id)
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Cannot list products", status_code=403)

    def test_filter_products_by_status(self):
        self.client.force_authenticate(user=self.superuser)
        product_1 = self.create_product(
            facility=self.facility,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
            status=ProductStatusOptions.active.value,
        )
        self.create_product(
            facility=self.facility,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
            status=ProductStatusOptions.inactive.value,
        )
        response = self.client.get(
            self.get_base_url(facility=self.facility.external_id),
            {"status": ProductStatusOptions.active.value},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(product_1.external_id))

    def test_filter_product_by_product_knowledge(self):
        self.client.force_authenticate(user=self.superuser)
        product_1 = self.create_product(
            facility=self.facility,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
            status=ProductStatusOptions.active.value,
        )
        product_knowledge_2 = self.create_product_knowledge(
            name="Another Product Knowledge",
            facility=self.facility,
            category=self.resource_category,
        )
        self.create_product(
            facility=self.facility,
            product_knowledge=product_knowledge_2,
            charge_item_definition=self.charge_item_definition,
            status=ProductStatusOptions.inactive.value,
        )
        response = self.client.get(
            self.get_base_url(facility=self.facility.external_id),
            {
                "product_knowledge": self.product_knowledge.slug,
                "status": ProductStatusOptions.active.value,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(product_1.external_id))

    def test_filter_product_by_facility(self):
        self.client.force_authenticate(user=self.superuser)
        product_1 = self.create_product(
            facility=self.facility,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
            status=ProductStatusOptions.active.value,
        )
        facility_2 = self.create_facility(name="Another Facility", user=self.superuser)
        self.create_product(
            facility=facility_2,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
            status=ProductStatusOptions.inactive.value,
        )
        response = self.client.get(
            self.get_base_url(facility=self.facility.external_id),
            {"facility": self.facility.external_id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(product_1.external_id))
