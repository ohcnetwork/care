from django.urls import reverse
from model_bakery import baker

from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.resources.inventory.inventory_item.sync_inventory_item import (
    sync_inventory_item,
)
from care.emr.resources.inventory.supply_delivery.spec import (
    SupplyDeliveryConditionOptions,
    SupplyDeliveryStatusOptions,
    SupplyDeliveryTypeOptions,
)
from care.security.permissions.supply_delivery import SupplyDeliveryPermissions
from care.utils.tests.base import CareAPITestBase


class TestSupplyDeliveryViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="testuser")
        self.superuser = self.create_super_user(username="superuser")
        self.patient = self.create_patient(name="Test Patient")
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility,
        )

        self.product_knowledge = baker.make(
            ProductKnowledge,
            facility=self.facility,
            slug=f"f-{self.facility.external_id}-product-knowledge",
        )
        self.charge_item_definition = baker.make(
            ChargeItemDefinition,
            facility=self.facility,
            slug=f"f-{self.facility.external_id}-charge-item-definition",
        )
        self.product = self.create_product(facility=self.facility)

        self.supplier = self.create_organization(name="Test Supplier")
        self.destination = self.create_facility_location(facility=self.facility)
        self.origin = self.create_facility_location(facility=self.facility)
        self.inventory_item_origin = self.create_inventory_item(
            product=self.product, location=self.origin, status="active"
        )
        self.inventory_item_destination = self.create_inventory_item(
            product=self.product, location=self.destination, status="active"
        )
        self.supply_request = self.create_supply_request(
            item=self.product_knowledge,
            status="requested",
            quantity=50,
            supplied_item_condition=SupplyDeliveryConditionOptions.normal.value,
            order=None,
        )
        self.role = self.create_role_with_permissions(
            permissions=[
                SupplyDeliveryPermissions.can_read_supply_delivery.name,
                SupplyDeliveryPermissions.can_write_supply_delivery.name,
            ]
        )
        self.base_url = reverse("supply_delivery-list")

        """ Setup for Delivery Orders and Locations for initial purchase orders"""

        self.delivery_order_destination_external = self.create_delivery_order(
            destination=self.destination,
            supplier=self.supplier,
        )
        self.delivery_order_origin_external = self.create_delivery_order(
            destination=self.origin,
            supplier=self.supplier,
        )
        self.delivery_order_internal = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
        )
        # Purchase Order of 1500 units to destination location
        self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=1500,
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.completed.value,
            supplied_inventory_item=self.inventory_item_destination,
        )

        # Purchase Order of 500 units from origin location
        self.create_supply_delivery(
            order=self.delivery_order_origin_external,
            supplied_item_quantity=500,
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.completed.value,
            supplied_inventory_item=self.inventory_item_origin,
        )
        self.inventory_item_origin.refresh_from_db()
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_origin.net_content, 500)
        self.assertEqual(self.inventory_item_destination.net_content, 1500)

    def get_detail_url(self, external_id):
        return reverse(
            "supply_delivery-detail",
            kwargs={
                "external_id": external_id,
            },
        )

    def create_product(self, **kwargs):
        from care.emr.models import Product

        return baker.make(
            Product,
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
            **kwargs,
        )

    def create_facility_location(self, facility, **kwargs):
        from care.emr.models import FacilityLocation, FacilityLocationOrganization

        location = baker.make(FacilityLocation, facility=facility, **kwargs)
        baker.make(
            FacilityLocationOrganization,
            location=location,
            organization=self.facility_organization,
        )
        return location

    def create_inventory_item(self, **kwargs):
        from care.emr.models import InventoryItem

        return baker.make(InventoryItem, **kwargs)

    def create_delivery_order(self, **kwargs):
        from care.emr.models import DeliveryOrder

        return baker.make(DeliveryOrder, **kwargs)

    def create_supply_request(self, **kwargs):
        from care.emr.models import SupplyRequest

        return baker.make(SupplyRequest, **kwargs)

    def create_supply_delivery_data(
        self,
        quantity=None,
        condition=None,
        delivery_type=None,
        supply_request=None,
        status=None,
        **kwargs,
    ):
        return {
            "supplied_item_quantity": quantity or 50,
            "status": status or SupplyDeliveryStatusOptions.in_progress.value,
            "supplied_item_condition": condition
            or SupplyDeliveryConditionOptions.normal.value,
            "delivery_type": delivery_type or SupplyDeliveryTypeOptions.product.value,
            "supply_request": supply_request or self.supply_request.external_id,
            **kwargs,
        }

    def create_supply_delivery(self, **kwargs):
        from care.emr.models import SupplyDelivery

        supply_delivery = baker.make(SupplyDelivery, **kwargs)
        if supply_delivery.order.origin:
            sync_inventory_item(inventory_item=supply_delivery.supplied_inventory_item)
        else:
            sync_inventory_item(
                location=supply_delivery.order.destination,
                product=supply_delivery.supplied_inventory_item.product,
            )
        return supply_delivery

    # Testcases for create supply delivery

    def test_create_supply_delivery_internally_as_superuser(self):
        """
        Test creating a supply delivery internally as a superuser from origin to destination
        and check if the inventory items are updated correctly.
        """
        self.client.force_authenticate(user=self.superuser)
        data = self.create_supply_delivery_data(
            supplied_inventory_item=self.inventory_item_origin.external_id,
            order=self.delivery_order_internal.external_id,
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["supplied_item_quantity"], 50)
        self.assertEqual(
            get_response.data["status"], SupplyDeliveryStatusOptions.in_progress.value
        )
        self.assertEqual(
            get_response.data["supplied_inventory_item"]["id"],
            str(self.inventory_item_origin.external_id),
        )
        self.inventory_item_origin.refresh_from_db()
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_origin.net_content, (float(450)))
        self.assertEqual(self.inventory_item_destination.net_content, (float(1500)))
        update_response = self.client.put(
            self.get_detail_url(response.data["id"]),
            {"status": SupplyDeliveryStatusOptions.completed.value},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, (float(1550)))

    def test_create_supply_delivery_externally_as_superuser(self):
        """
        Test creating a supply delivery externally as a superuser to destination location
        and check if the inventory items are updated correctly.
        """
        self.client.force_authenticate(user=self.superuser)
        data = self.create_supply_delivery_data(
            supplied_item=self.product.external_id,
            order=self.delivery_order_destination_external.external_id,
            quantity=500,
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(response.data["id"]), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["supplied_item_quantity"], 500)
        self.assertEqual(
            get_response.data["status"], SupplyDeliveryStatusOptions.in_progress.value
        )
        self.assertEqual(
            get_response.data["supplied_inventory_item"]["id"],
            str(self.inventory_item_destination.external_id),
        )
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, (float(1500)))
        update_response = self.client.put(
            self.get_detail_url(response.data["id"]),
            {"status": SupplyDeliveryStatusOptions.completed.value},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, (float(2000)))

    def test_create_supply_delivery_internally_as_user_with_permissions(self):
        """
        Test creating a internal supply delivery as a user with permissions
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            facility_organization=self.facility_organization,
            user=self.user,
            role=self.role,
        )
        data = self.create_supply_delivery_data(
            supplied_inventory_item=self.inventory_item_origin.external_id,
            order=self.delivery_order_internal.external_id,
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["supplied_item_quantity"], 50)
        self.assertEqual(
            get_response.data["status"], SupplyDeliveryStatusOptions.in_progress.value
        )
        self.assertEqual(
            get_response.data["supplied_inventory_item"]["id"],
            str(self.inventory_item_origin.external_id),
        )
        self.inventory_item_origin.refresh_from_db()
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_origin.net_content, (float(450)))
        self.assertEqual(self.inventory_item_destination.net_content, (float(1500)))
        update_response = self.client.put(
            self.get_detail_url(response.data["id"]),
            {"status": SupplyDeliveryStatusOptions.completed.value},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, (float(1550)))

    def test_create_supply_delivery_externally_as_user_with_permissions(self):
        """
        Test creating a external supply delivery as a user with permissions
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            facility_organization=self.facility_organization,
            user=self.user,
            role=self.role,
        )
        data = self.create_supply_delivery_data(
            supplied_item=self.product.external_id,
            order=self.delivery_order_destination_external.external_id,
            quantity=500,
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(response.data["id"]), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["supplied_item_quantity"], 500)
        self.assertEqual(
            get_response.data["status"], SupplyDeliveryStatusOptions.in_progress.value
        )
        self.assertEqual(
            get_response.data["supplied_inventory_item"]["id"],
            str(self.inventory_item_destination.external_id),
        )
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, (float(1500)))
        update_response = self.client.put(
            self.get_detail_url(response.data["id"]),
            {"status": SupplyDeliveryStatusOptions.completed.value},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, (float(2000)))

    def test_create_supply_delivery_as_user_without_permissions(self):
        """
        Test creating a supply delivery as a user without permissions
        """
        self.client.force_authenticate(user=self.user)
        data = self.create_supply_delivery_data(
            supplied_item=self.product.external_id,
            order=self.delivery_order_destination_external.external_id,
            quantity=500,
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Cannot write supply requests", status_code=403)

    def test_create_supply_delivery_as_superuser_with_insufficient_stock(self):
        """
        Test creating a supply delivery as a superuser with insufficient stock in internal delivery
        The origin location has only 500 units, trying to deliver 501 should fail
        """
        self.client.force_authenticate(user=self.superuser)
        data = self.create_supply_delivery_data(
            supplied_inventory_item=self.inventory_item_origin.external_id,
            order=self.delivery_order_internal.external_id,
            quantity=501,
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Insufficient stock", status_code=400)

    def test_create_supply_delivery_with_different_origin_and_inventory_item_location(
        self,
    ):
        """
        Test creating a supply delivery as a superuser with different origin location in order
        and inventory item location
        """
        self.client.force_authenticate(user=self.superuser)
        data = self.create_supply_delivery_data(
            supplied_inventory_item=self.inventory_item_destination.external_id,
            order=self.delivery_order_internal.external_id,
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Supplied inventory item is not part of the origin or its children",
            status_code=400,
        )

    def test_create_supply_delivery_internally_with_order_but_no_supplied_inventory_item(
        self,
    ):
        """
        Test creating a supply delivery as a superuser with order having order origin
        but no supplied_inventory_item provided
        """
        self.client.force_authenticate(user=self.superuser)
        data = self.create_supply_delivery_data(
            order=self.delivery_order_internal.external_id,
            supplied_item=self.product.external_id,
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "supplied_inventory_item is required when origin is provided",
            status_code=400,
        )

    def test_create_supply_delivery_externally_with_order_but_no_supplied_item(self):
        """
        Test creating a supply delivery as a superuser with order having order origin
        but no supplied_item provided
        """
        self.client.force_authenticate(user=self.superuser)
        data = self.create_supply_delivery_data(
            order=self.delivery_order_destination_external.external_id
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "supplied_item is required when origin is not provided",
            status_code=400,
        )

    def test_create_supply_delivery_with_both_supplied_item_and_inventory_item(self):
        """
        Test creating a supply delivery as a superuser with both supplied_item and supplied_inventory_item
        """
        self.client.force_authenticate(user=self.superuser)
        data = self.create_supply_delivery_data(
            supplied_item=self.product.external_id,
            supplied_inventory_item=self.inventory_item_destination.external_id,
            order=self.delivery_order_destination_external.external_id,
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "supplied_item and supplied_inventory_item cannot both be provided",
            status_code=400,
        )

    # Testcases for update supply delivery

    def test_update_supply_delivery_as_superuser(self):
        """
        Test updating an external supply delivery as a superuser
        """
        self.client.force_authenticate(user=self.superuser)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=500,
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        update_response = self.client.put(
            self.get_detail_url(supply_delivery.external_id),
            {"status": SupplyDeliveryStatusOptions.completed.value},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, (float(2000)))
        get_response = self.client.get(
            self.get_detail_url(supply_delivery.external_id), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["status"], "completed")

    def test_update_supply_delivery_as_user_with_permissions(self):
        """
        Test updating an external supply delivery as a user with permissions
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            facility_organization=self.facility_organization,
            user=self.user,
            role=self.role,
        )
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=500,
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        update_response = self.client.put(
            self.get_detail_url(supply_delivery.external_id),
            {"status": SupplyDeliveryStatusOptions.completed.value},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, (float(2000)))
        get_response = self.client.get(
            self.get_detail_url(supply_delivery.external_id), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["status"], "completed")

    def test_update_supply_delivery_as_user_without_permissions(self):
        """
        Test updating an external supply delivery as a user without permissions
        """
        self.client.force_authenticate(user=self.user)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=500,
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        update_response = self.client.put(
            self.get_detail_url(supply_delivery.external_id),
            {"status": SupplyDeliveryStatusOptions.completed.value},
            format="json",
        )
        self.assertEqual(update_response.status_code, 403)
        self.assertContains(
            update_response, "Cannot write supply requests", status_code=403
        )

    def test_update_supply_delivery_with_already_completed(self):
        """
        Test updating an external supply delivery which is already completed as a superuser
        """
        self.client.force_authenticate(user=self.superuser)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=500,
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.completed.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        update_response = self.client.put(
            self.get_detail_url(supply_delivery.external_id),
            {"status": SupplyDeliveryStatusOptions.in_progress.value},
            format="json",
        )
        self.assertEqual(update_response.status_code, 400)
        self.assertContains(
            update_response,
            "Supply delivery already completed",
            status_code=400,
        )
