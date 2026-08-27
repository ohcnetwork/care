import datetime

from django.urls import reverse
from model_bakery import baker

from care.security.permissions.inventory_item import InventoryItemPermissions
from care.utils.tests.base import CareAPITestBase


class InventoryItemAPITest(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="testuser")
        self.super_user = self.create_super_user()
        self.facility = self.create_facility(name="Test Facility", user=self.super_user)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, org_type="root"
        )
        self.role = self.create_role_with_permissions(
            permissions=[
                InventoryItemPermissions.can_read_inventory_item.name,
            ]
        )
        self.facility_location = self.create_facility_location(self.facility)
        self.base_url = reverse(
            "inventory-item-list",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "location_external_id": self.facility_location.external_id,
            },
        )

    def get_detail_url(self, facility, location, external_id):
        return reverse(
            "inventory-item-detail",
            kwargs={
                "facility_external_id": facility,
                "location_external_id": location,
                "external_id": external_id,
            },
        )

    def create_facility_location(self, facility, **kwargs):
        location = baker.make(
            "emr.FacilityLocation", facility=facility, name="Test Location", **kwargs
        )

        baker.make(
            "emr.FacilityLocationOrganization",
            location=location,
            organization=self.facility_organization,
        )
        return location

    def calculate_slug(self, slug_value, facility):
        if facility:
            return f"f-{facility.external_id}-{slug_value}"
        return f"i-{slug_value}"

    def create_product_knowledge(self, facility, **kwargs):
        slug_value = kwargs.get("slug", "default_slug")
        slug = self.calculate_slug(slug_value, facility)
        return baker.make(
            "emr.ProductKnowledge", facility=facility, slug=slug, **kwargs
        )

    def create_charge_item_definition(self, facility, **kwargs):
        slug_value = kwargs.get("slug", "default_slug")
        slug = self.calculate_slug(slug_value, facility)
        return baker.make(
            "emr.ChargeItemDefinition", facility=facility, slug=slug, **kwargs
        )

    def create_product(
        self, facility, product_knowledge, charge_item_definition=None, **kwargs
    ):
        return baker.make(
            "emr.Product",
            facility=facility,
            product_knowledge=product_knowledge,
            charge_item_definition=charge_item_definition,
            **kwargs,
        )

    def create_inventory_item(self, facility, location, status=None, **kwargs):
        product_knowledge = self.create_product_knowledge(facility=facility)
        charge_item_definition = self.create_charge_item_definition(facility=facility)
        product = self.create_product(
            facility=facility,
            product_knowledge=product_knowledge,
            charge_item_definition=charge_item_definition,
            **kwargs,
        )
        return baker.make(
            "emr.InventoryItem",
            product=product,
            location=location,
            status=status or "active",
        )

    # Testcases for retrieving inventory items

    def test_retrieve_inventory_item_as_super_user(self):
        self.client.force_authenticate(user=self.super_user)
        inventory_item = self.create_inventory_item(
            facility=self.facility, location=self.facility_location
        )
        response = self.client.get(
            self.get_detail_url(
                facility=self.facility.external_id,
                location=self.facility_location.external_id,
                external_id=inventory_item.external_id,
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(inventory_item.external_id))

    def test_retrieve_inventory_item_as_user_with_permission(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        inventory_item = self.create_inventory_item(
            facility=self.facility, location=self.facility_location
        )
        response = self.client.get(
            self.get_detail_url(
                facility=self.facility.external_id,
                location=self.facility_location.external_id,
                external_id=inventory_item.external_id,
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(inventory_item.external_id))

    def test_retrieve_inventory_item_with_invalid_location(self):
        self.client.force_authenticate(user=self.super_user)
        other_location = self.create_facility_location(facility=self.facility)
        inventory_item = self.create_inventory_item(
            facility=self.facility, location=self.facility_location
        )
        response = self.client.get(
            self.get_detail_url(
                facility=self.facility.external_id,
                location=other_location.external_id,
                external_id=inventory_item.external_id,
            )
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Inventory item does not belong to the specified location",
            status_code=400,
        )

    def test_retrieve_inventory_item_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        inventory_item = self.create_inventory_item(
            facility=self.facility, location=self.facility_location
        )
        response = self.client.get(
            self.get_detail_url(
                facility=self.facility.external_id,
                location=self.facility_location.external_id,
                external_id=inventory_item.external_id,
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to read inventory items",
        )

    # Testcases for listing inventory items

    def test_listing_inventory_items_product_knowledge_filter(self):
        self.client.force_authenticate(user=self.super_user)
        inventory = self.create_inventory_item(
            facility=self.facility, location=self.facility_location
        )
        self.create_inventory_item(
            facility=self.facility, location=self.facility_location
        )
        response = self.client.get(
            self.base_url
            + f"?product_knowledge={inventory.product.product_knowledge.external_id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(inventory.external_id))

    def test_listing_inventory_items_status_filter(self):
        self.client.force_authenticate(user=self.super_user)
        inventory = self.create_inventory_item(
            facility=self.facility, location=self.facility_location, status="active"
        )
        self.create_inventory_item(
            facility=self.facility, location=self.facility_location, status="inactive"
        )
        response = self.client.get(self.base_url + f"?status={inventory.status}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(inventory.external_id))

    def test_listing_inventory_items_product_expiration_date_filter(self):
        self.client.force_authenticate(user=self.super_user)
        now = datetime.datetime.now(datetime.UTC)
        unexpired_inventory = self.create_inventory_item(
            facility=self.facility,
            location=self.facility_location,
            expiration_date=now + datetime.timedelta(days=30),
        )
        self.create_inventory_item(
            facility=self.facility,
            location=self.facility_location,
            expiration_date=now - datetime.timedelta(days=30),
        )
        response = self.client.get(
            self.base_url,
            {"product_expiration_date_after": now.date().isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(unexpired_inventory.external_id)
        )

    def test_listing_inventory_items_include_children_filter(self):
        self.client.force_authenticate(user=self.super_user)
        child_location = self.create_facility_location(
            facility=self.facility, parent=self.facility_location
        )
        child_location.parent_cache = [self.facility_location.id]
        child_location.save()
        inventory1 = self.create_inventory_item(
            facility=self.facility, location=self.facility_location
        )
        inventory2 = self.create_inventory_item(
            facility=self.facility, location=child_location
        )
        response = self.client.get(self.base_url, {"include_children": "true"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][1]["id"], str(inventory1.external_id))
        self.assertEqual(response.data["results"][0]["id"], str(inventory2.external_id))

    def test_listing_inventory_items_include_children_filter_as_user_without_permission(
        self,
    ):
        self.client.force_authenticate(user=self.user)
        child_location = self.create_facility_location(
            facility=self.facility, parent=self.facility_location
        )
        child_location.parent_cache = [self.facility_location.id]
        child_location.save()
        self.create_inventory_item(
            facility=self.facility, location=self.facility_location
        )
        self.create_inventory_item(facility=self.facility, location=child_location)
        response = self.client.get(self.base_url, {"include_children": "true"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to read inventory items",
        )

    def test_listing_inventory_items_include_children_as_false(self):
        self.client.force_authenticate(user=self.super_user)
        child_location = self.create_facility_location(
            facility=self.facility, parent=self.facility_location
        )
        child_location.parent_cache = [self.facility_location.id]
        child_location.save()
        inventory1 = self.create_inventory_item(
            facility=self.facility, location=self.facility_location
        )
        self.create_inventory_item(facility=self.facility, location=child_location)
        response = self.client.get(self.base_url, {"include_children": "false"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(inventory1.external_id))
