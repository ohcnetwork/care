from decimal import Decimal

from django.urls import reverse
from model_bakery import baker

from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.resources.inventory.inventory_item.sync_inventory_item import (
    sync_inventory_item,
)
from care.emr.resources.inventory.supply_delivery.delivery_order import (
    SupplyDeliveryOrderStatusOptions,
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
        self.request_order_destination_external = self.create_request_order(
            supplier=self.supplier,
            destination=self.destination,
        )
        self.request_order_internal = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.supply_request_destination_external = self.create_supply_request(
            item=self.product_knowledge,
            status="active",
            quantity=Decimal(1500),
            supplied_item_condition=SupplyDeliveryConditionOptions.normal.value,
            order=self.request_order_destination_external,
        )
        self.supply_request_internal = self.create_supply_request(
            item=self.product_knowledge,
            status="active",
            quantity=Decimal(200),
            supplied_item_condition=SupplyDeliveryConditionOptions.normal.value,
            order=self.request_order_internal,
        )
        self.role = self.create_role_with_permissions(
            permissions=[
                SupplyDeliveryPermissions.can_read_supply_delivery.name,
                SupplyDeliveryPermissions.can_write_supply_delivery.name,
            ]
        )
        self.base_url = reverse("supply_delivery-list")
        self.delivery_orders_url = reverse("supply_delivery-delivery-orders")

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
        self.purchase_order_destination = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=Decimal(1500),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.completed.value,
            supplied_inventory_item=self.inventory_item_destination,
            supply_request=self.supply_request_destination_external,
        )

        # Purchase Order of 500 units from origin location
        self.purchase_order_origin = self.create_supply_delivery(
            order=self.delivery_order_origin_external,
            supplied_item_quantity=Decimal(500),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.completed.value,
            supplied_inventory_item=self.inventory_item_origin,
        )
        self.inventory_item_origin.refresh_from_db()
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_origin.net_content, Decimal(500))
        self.assertEqual(self.inventory_item_destination.net_content, Decimal(1500))

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

    def create_request_order(self, **kwargs):
        from care.emr.models import RequestOrder

        return baker.make(RequestOrder, **kwargs)

    def create_supply_delivery_data(
        self,
        quantity=None,
        condition=None,
        delivery_type=None,
        status=None,
        **kwargs,
    ):
        return {
            "supplied_item_quantity": quantity or Decimal(50),
            "status": status or SupplyDeliveryStatusOptions.in_progress.value,
            "supplied_item_condition": condition
            or SupplyDeliveryConditionOptions.normal.value,
            "delivery_type": delivery_type or SupplyDeliveryTypeOptions.product.value,
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
        self.assertEqual(get_response.data["supplied_item_quantity"], "50.000000")
        self.assertEqual(
            get_response.data["status"], SupplyDeliveryStatusOptions.in_progress.value
        )
        self.assertEqual(
            get_response.data["supplied_inventory_item"]["id"],
            str(self.inventory_item_origin.external_id),
        )
        self.inventory_item_origin.refresh_from_db()
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_origin.net_content, Decimal(450))
        self.assertEqual(self.inventory_item_destination.net_content, Decimal(1500))
        update_response = self.client.put(
            self.get_detail_url(response.data["id"]),
            {"status": SupplyDeliveryStatusOptions.completed.value},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, Decimal(1550))

    def test_create_supply_delivery_externally_as_superuser(self):
        """
        Test creating a supply delivery externally as a superuser to destination location
        and check if the inventory items are updated correctly.
        """
        self.client.force_authenticate(user=self.superuser)
        data = self.create_supply_delivery_data(
            supplied_item=self.product.external_id,
            order=self.delivery_order_destination_external.external_id,
            quantity=Decimal(500),
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(response.data["id"]), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["supplied_item_quantity"], "500.000000")
        self.assertEqual(
            get_response.data["status"], SupplyDeliveryStatusOptions.in_progress.value
        )
        self.assertEqual(
            get_response.data["supplied_inventory_item"]["id"],
            str(self.inventory_item_destination.external_id),
        )
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, Decimal(1500))
        update_response = self.client.put(
            self.get_detail_url(response.data["id"]),
            {"status": SupplyDeliveryStatusOptions.completed.value},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, Decimal(2000))

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
        self.assertEqual(get_response.data["supplied_item_quantity"], "50.000000")
        self.assertEqual(
            get_response.data["status"], SupplyDeliveryStatusOptions.in_progress.value
        )
        self.assertEqual(
            get_response.data["supplied_inventory_item"]["id"],
            str(self.inventory_item_origin.external_id),
        )
        self.inventory_item_origin.refresh_from_db()
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_origin.net_content, Decimal(450))
        self.assertEqual(self.inventory_item_destination.net_content, Decimal(1500))
        update_response = self.client.put(
            self.get_detail_url(response.data["id"]),
            {"status": SupplyDeliveryStatusOptions.completed.value},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, Decimal(1550))

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
            quantity=Decimal(500),
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(response.data["id"]), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["supplied_item_quantity"], "500.000000")
        self.assertEqual(
            get_response.data["status"], SupplyDeliveryStatusOptions.in_progress.value
        )
        self.assertEqual(
            get_response.data["supplied_inventory_item"]["id"],
            str(self.inventory_item_destination.external_id),
        )
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, (Decimal(1500)))
        update_response = self.client.put(
            self.get_detail_url(response.data["id"]),
            {"status": SupplyDeliveryStatusOptions.completed.value},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, (Decimal(2000)))

    def test_create_external_supply_delivery_as_user_without_permissions(self):
        """
        Test creating a external supply delivery as a user without permissions
        """
        self.client.force_authenticate(user=self.user)
        data = self.create_supply_delivery_data(
            supplied_item=self.product.external_id,
            order=self.delivery_order_destination_external.external_id,
            quantity=Decimal(500),
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Cannot write supply requests", status_code=403)

    def test_create_internal_supply_delivery_as_user_without_permissions(self):
        """
        Test creating a internal supply delivery as a user without permissions
        """
        self.client.force_authenticate(user=self.user)
        data = self.create_supply_delivery_data(
            supplied_inventory_item=self.inventory_item_origin.external_id,
            order=self.delivery_order_internal.external_id,
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
            quantity=Decimal(501),
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

    def test_create_supply_delivery_with_completed_order(self):
        """
        Test creating a supply delivery as a superuser with order which is already completed
        """
        self.client.force_authenticate(user=self.superuser)
        self.delivery_order_internal.status = (
            SupplyDeliveryOrderStatusOptions.completed.value
        )
        self.delivery_order_internal.save()
        data = self.create_supply_delivery_data(
            supplied_inventory_item=self.inventory_item_origin.external_id,
            order=self.delivery_order_internal.external_id,
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Delivery order is completed",
            status_code=400,
        )

    def test_create_supply_delivery_with_abandoned_order(self):
        """
        Test creating a supply delivery as a superuser with order which is already abandoned
        """
        self.client.force_authenticate(user=self.superuser)
        self.delivery_order_internal.status = (
            SupplyDeliveryOrderStatusOptions.abandoned.value
        )
        self.delivery_order_internal.save()
        data = self.create_supply_delivery_data(
            supplied_inventory_item=self.inventory_item_origin.external_id,
            order=self.delivery_order_internal.external_id,
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Delivery order is abandoned or entered in error",
            status_code=400,
        )

    def test_create_supply_delivery_with_entered_in_error_order(self):
        """
        Test creating a supply delivery as a superuser with order which is already entered in error
        """
        self.client.force_authenticate(user=self.superuser)
        self.delivery_order_internal.status = (
            SupplyDeliveryOrderStatusOptions.entered_in_error.value
        )
        self.delivery_order_internal.save()
        data = self.create_supply_delivery_data(
            supplied_inventory_item=self.inventory_item_origin.external_id,
            order=self.delivery_order_internal.external_id,
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Delivery order is abandoned or entered in error",
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
            supplied_item_quantity=Decimal(500),
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
        self.assertEqual(self.inventory_item_destination.net_content, (Decimal(2000)))
        get_response = self.client.get(
            self.get_detail_url(supply_delivery.external_id), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["status"], "completed")

    def test_update_external_supply_delivery_as_user_with_permissions(self):
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
            supplied_item_quantity=Decimal(500),
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
        self.assertEqual(self.inventory_item_destination.net_content, (Decimal(2000)))
        get_response = self.client.get(
            self.get_detail_url(supply_delivery.external_id), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["status"], "completed")

    def test_update_internal_supply_delivery_as_user_with_permissions(self):
        """
        Test updating an internal supply delivery as a user with permissions
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            facility_organization=self.facility_organization,
            user=self.user,
            role=self.role,
        )
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_internal,
            supplied_item_quantity=Decimal(200),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_origin,
        )
        update_response = self.client.put(
            self.get_detail_url(supply_delivery.external_id),
            {"status": SupplyDeliveryStatusOptions.completed.value},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, Decimal(1700))
        get_response = self.client.get(
            self.get_detail_url(supply_delivery.external_id), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["status"], "completed")

    def test_update_external_supply_delivery_as_user_without_permissions(self):
        """
        Test updating an external supply delivery as a user without permissions
        """
        self.client.force_authenticate(user=self.user)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=Decimal(500),
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

    def test_update_internal_supply_delivery_as_user_without_permissions(self):
        """
        Test updating an internal supply delivery as a user without permissions
        """
        self.client.force_authenticate(user=self.user)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_internal,
            supplied_item_quantity=Decimal(500),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_origin,
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

    def test_update_status_of_completed_internal_supply_delivery(self):
        """
        Test updating an internal supply delivery which is already completed as a superuser
        """
        self.client.force_authenticate(user=self.superuser)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_internal,
            supplied_item_quantity=Decimal(200),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.completed.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        update_response = self.client.put(
            self.get_detail_url(supply_delivery.external_id),
            {"status": SupplyDeliveryStatusOptions.abandoned.value},
            format="json",
        )
        self.assertEqual(update_response.status_code, 400)
        self.assertContains(
            update_response,
            "Supply delivery already completed",
            status_code=400,
        )

    def test_update_supply_delivery_with_no_status_change(self):
        """
        Test updating an external supply delivery without changing the status
        """
        self.client.force_authenticate(user=self.superuser)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=Decimal(500),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        update_response = self.client.put(
            self.get_detail_url(supply_delivery.external_id),
            {
                "status": SupplyDeliveryStatusOptions.in_progress.value,
                "supplied_item_condition": SupplyDeliveryConditionOptions.damaged.value,
            },
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(supply_delivery.external_id), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["status"], SupplyDeliveryStatusOptions.in_progress.value
        )
        self.assertEqual(
            get_response.data["supplied_item_condition"],
            SupplyDeliveryConditionOptions.damaged.value,
        )

    def test_update_supply_delivery_with_status_entered_in_error(self):
        """
        Test updating a supply delivery with status as entered in error
        """
        self.client.force_authenticate(user=self.superuser)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=Decimal(500),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.entered_in_error.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        response = self.client.put(
            self.get_detail_url(supply_delivery.external_id),
            {"status": SupplyDeliveryStatusOptions.in_progress.value},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Supply delivery is abandoned or entered in error",
            status_code=400,
        )

    def test_update_supply_delivery_with_status_abandoned(self):
        """
        Test updating a supply delivery with status as abandoned
        """
        self.client.force_authenticate(user=self.superuser)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=Decimal(500),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.abandoned.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        response = self.client.put(
            self.get_detail_url(supply_delivery.external_id),
            {"status": SupplyDeliveryStatusOptions.in_progress.value},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Supply delivery is abandoned or entered in error",
            status_code=400,
        )

    # Testcases for retrieve supply delivery

    def test_retrieve_supply_delivery_as_superuser(self):
        """
        Test retrieving a supply delivery as a superuser
        """
        self.client.force_authenticate(user=self.superuser)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=Decimal(500),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        get_response = self.client.get(
            self.get_detail_url(supply_delivery.external_id), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["supplied_item_quantity"], "500.000000")
        self.assertEqual(
            get_response.data["status"], SupplyDeliveryStatusOptions.in_progress.value
        )
        self.assertEqual(
            get_response.data["supplied_inventory_item"]["id"],
            str(self.inventory_item_destination.external_id),
        )

    def test_retrieve_supply_delivery_as_user_with_permissions(self):
        """
        Test retrieving a supply delivery as a user with permissions
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            facility_organization=self.facility_organization,
            user=self.user,
            role=self.role,
        )
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=Decimal(500),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        get_response = self.client.get(
            self.get_detail_url(supply_delivery.external_id), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["supplied_item_quantity"], "500.000000")
        self.assertEqual(
            get_response.data["status"], SupplyDeliveryStatusOptions.in_progress.value
        )
        self.assertEqual(
            get_response.data["supplied_inventory_item"]["id"],
            str(self.inventory_item_destination.external_id),
        )

    def test_retrieve_supply_delivery_as_user_without_permissions(self):
        """Test retrieving a supply delivery as a user without permissions"""
        self.client.force_authenticate(user=self.user)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=Decimal(500),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        get_response = self.client.get(
            self.get_detail_url(supply_delivery.external_id), format="json"
        )
        self.assertEqual(get_response.status_code, 403)
        self.assertContains(
            get_response, "Cannot read supply requests", status_code=403
        )

    # Testcases for list supply delivery

    def test_list_supply_delivery_as_superuser_with_order_filter(self):
        """Test listing supply deliveries as a superuser with order queryset filter"""
        self.client.force_authenticate(user=self.superuser)
        list_response = self.client.get(
            self.base_url,
            {"order": self.delivery_order_destination_external.external_id},
            format="json",
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(
            list_response.data["results"][0]["status"],
            SupplyDeliveryStatusOptions.completed.value,
        )
        self.assertEqual(
            list_response.data["results"][0]["supplied_item_quantity"], "1500.000000"
        )
        self.assertEqual(
            list_response.data["results"][0]["id"],
            str(self.purchase_order_destination.external_id),
        )

    def test_list_supply_delivery_as_user_with_permissions_with_order_filter(self):
        """Test listing supply deliveries as a user with permissions"""
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            facility_organization=self.facility_organization,
            user=self.user,
            role=self.role,
        )
        list_response = self.client.get(
            self.base_url,
            {"order": self.delivery_order_origin_external.external_id},
            format="json",
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(
            list_response.data["results"][0]["id"],
            str(self.purchase_order_origin.external_id),
        )
        self.assertEqual(
            list_response.data["results"][0]["status"],
            SupplyDeliveryStatusOptions.completed.value,
        )
        self.assertEqual(
            list_response.data["results"][0]["supplied_item_quantity"], "500.000000"
        )

    def test_list_supply_delivery_as_user_without_permissions(self):
        """Test listing supply deliveries as a user without 'can_list_facility_supply_delivery' permissions"""
        self.client.force_authenticate(user=self.user)
        list_response = self.client.get(
            self.base_url,
            {"order": self.delivery_order_origin_external.external_id},
            format="json",
        )
        self.assertEqual(list_response.status_code, 403)
        self.assertContains(
            list_response, "Cannot read supply requests", status_code=403
        )

    def test_list_supply_delivery_as_superuser_without_filters(self):
        """Test listing supply deliveries as a superuser without any filters"""
        self.client.force_authenticate(user=self.superuser)
        list_response = self.client.get(self.base_url, format="json")
        self.assertEqual(list_response.status_code, 400)
        self.assertContains(
            list_response,
            "No filters provided",
            status_code=400,
        )

    def test_list_supply_delivery_as_superuser_with_destination_filter(self):
        """Test listing supply deliveries as a superuser with destination location filter"""
        self.client.force_authenticate(user=self.superuser)
        list_response = self.client.get(
            self.base_url, {"destination": self.destination.external_id}, format="json"
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(
            list_response.data["results"][0]["id"],
            str(self.purchase_order_destination.external_id),
        )
        self.assertEqual(
            list_response.data["results"][0]["status"],
            SupplyDeliveryStatusOptions.completed.value,
        )
        self.assertEqual(
            list_response.data["results"][0]["supplied_item_quantity"], "1500.000000"
        )

    def test_list_supply_delivery_as_superuser_with_origin_filter(self):
        """Test listing supply deliveries as a superuser with origin location filter"""
        self.client.force_authenticate(user=self.superuser)
        internal_delivery = self.create_supply_delivery(
            order=self.delivery_order_internal,
            supplied_item_quantity=Decimal(200),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.completed.value,
            supplied_inventory_item=self.inventory_item_origin,
        )
        list_response = self.client.get(
            self.base_url, {"origin": self.origin.external_id}, format="json"
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(
            list_response.data["results"][0]["id"], str(internal_delivery.external_id)
        )
        self.assertEqual(
            list_response.data["results"][0]["status"],
            SupplyDeliveryStatusOptions.completed.value,
        )
        self.assertEqual(
            list_response.data["results"][0]["supplied_item_quantity"], "200.000000"
        )
        self.assertEqual(
            list_response.data["results"][0]["supplied_inventory_item"]["id"],
            str(self.inventory_item_origin.external_id),
        )
        self.assertEqual(
            list_response.data["results"][0]["supplied_inventory_item"]["net_content"],
            "300.000000",
        )

    def test_list_supply_delivery_as_user_with_permissions_with_destination_filter(
        self,
    ):
        """Test listing supply deliveries as a user with permissions with destination location filter"""
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            facility_organization=self.facility_organization,
            user=self.user,
            role=self.role,
        )
        list_response = self.client.get(
            self.base_url, {"destination": self.destination.external_id}, format="json"
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(
            list_response.data["results"][0]["id"],
            str(self.purchase_order_destination.external_id),
        )
        self.assertEqual(
            list_response.data["results"][0]["status"],
            SupplyDeliveryStatusOptions.completed.value,
        )
        self.assertEqual(
            list_response.data["results"][0]["supplied_item_quantity"], "1500.000000"
        )

    def test_list_supply_delivery_as_user_with_permissions_with_origin_filter(self):
        """Test listing supply deliveries as a user with permissions with origin location filter"""
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            facility_organization=self.facility_organization,
            user=self.user,
            role=self.role,
        )
        internal_delivery = self.create_supply_delivery(
            order=self.delivery_order_internal,
            supplied_item_quantity=200,
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.completed.value,
            supplied_inventory_item=self.inventory_item_origin,
        )
        list_response = self.client.get(
            self.base_url, {"origin": self.origin.external_id}, format="json"
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(
            list_response.data["results"][0]["id"], str(internal_delivery.external_id)
        )
        self.assertEqual(
            list_response.data["results"][0]["status"],
            SupplyDeliveryStatusOptions.completed.value,
        )
        self.assertEqual(
            list_response.data["results"][0]["supplied_item_quantity"], "200.000000"
        )
        self.assertEqual(
            list_response.data["results"][0]["supplied_inventory_item"]["id"],
            str(self.inventory_item_origin.external_id),
        )
        self.assertEqual(
            list_response.data["results"][0]["supplied_inventory_item"]["net_content"],
            "300.000000",
        )

    def test_list_supply_delivery_as_user_without_permissions_with_destination_filter(
        self,
    ):
        """Test listing supply deliveries as a user without permissions with destination location filter"""
        self.client.force_authenticate(user=self.user)
        list_response = self.client.get(
            self.base_url, {"destination": self.destination.external_id}, format="json"
        )
        self.assertEqual(list_response.status_code, 403)
        self.assertContains(
            list_response, "Cannot list supply requests", status_code=403
        )

    def test_list_supply_delivery_as_user_without_permissions_with_origin_filter(self):
        """Test listing supply deliveries as a user without permissions with origin location filter"""
        self.client.force_authenticate(user=self.user)
        list_response = self.client.get(
            self.base_url, {"origin": self.origin.external_id}, format="json"
        )
        self.assertEqual(list_response.status_code, 403)
        self.assertContains(
            list_response, "Cannot list supply requests", status_code=403
        )

    def test_list_supply_delivery_with_include_children_as_true(self):
        """Test listing supply deliveries with include_children filter as true , should return deliveries to origin and its child locations"""

        self.client.force_authenticate(user=self.superuser)
        child_location = self.create_facility_location(
            name="Child Location", parent=self.origin, facility=self.facility
        )
        inventory_item_child = self.create_inventory_item(
            product=self.product,
            location=child_location,
            status="active",
        )
        child_delivery_order_external = self.create_delivery_order(
            destination=child_location,
            supplier=self.supplier,
        )
        self.create_supply_delivery(
            order=child_delivery_order_external,
            supplied_item_quantity=Decimal(200),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.completed.value,
            supplied_inventory_item=inventory_item_child,
        )

        child_delivery_order_internal = self.create_delivery_order(
            origin=child_location,
            destination=self.destination,
        )
        supply_delivery_parent = self.create_supply_delivery(
            order=self.delivery_order_internal,
            supplied_item_quantity=Decimal(200),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.completed.value,
            supplied_inventory_item=self.inventory_item_origin,
        )
        supply_delivery_child = self.create_supply_delivery(
            supplied_item_quantity=Decimal(100),
            order=child_delivery_order_internal,
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.completed.value,
            supplied_inventory_item=inventory_item_child,
        )
        list_response = self.client.get(
            self.base_url,
            {"origin": self.origin.external_id, "include_children": "true"},
            format="json",
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 2)
        self.assertEqual(
            list_response.data["results"][0]["id"],
            str(supply_delivery_child.external_id),
        )
        self.assertEqual(
            list_response.data["results"][1]["id"],
            str(supply_delivery_parent.external_id),
        )

        self.assertEqual(
            list_response.data["results"][0]["supplied_item_quantity"], "100.000000"
        )
        self.assertEqual(
            list_response.data["results"][1]["supplied_item_quantity"], "200.000000"
        )
        self.assertEqual(
            list_response.data["results"][0]["supplied_inventory_item"]["id"],
            str(inventory_item_child.external_id),
        )
        self.assertEqual(
            list_response.data["results"][0]["supplied_inventory_item"]["net_content"],
            "100.000000",
        )
        self.assertEqual(
            list_response.data["results"][1]["supplied_inventory_item"]["id"],
            str(self.inventory_item_origin.external_id),
        )
        self.assertEqual(
            list_response.data["results"][1]["supplied_inventory_item"]["net_content"],
            "300.000000",
        )

    def test_list_supply_delivery_with_include_children_as_false(self):
        """Test listing supply deliveries with include_children filter as false should return deliveries to origin location only"""
        self.client.force_authenticate(user=self.superuser)
        child_location = self.create_facility_location(
            name="Child Location", parent=self.origin, facility=self.facility
        )
        inventory_item_child = self.create_inventory_item(
            product=self.product,
            location=child_location,
            status="active",
        )
        child_delivery_order_external = self.create_delivery_order(
            destination=child_location,
            supplier=self.supplier,
        )
        self.create_supply_delivery(
            order=child_delivery_order_external,
            supplied_item_quantity=200,
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.completed.value,
            supplied_inventory_item=inventory_item_child,
        )

        child_delivery_order_internal = self.create_delivery_order(
            origin=child_location,
            destination=self.destination,
        )
        supply_delivery_parent = self.create_supply_delivery(
            order=self.delivery_order_internal,
            supplied_item_quantity=200,
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.completed.value,
            supplied_inventory_item=self.inventory_item_origin,
        )
        self.create_supply_delivery(
            supplied_item_quantity=100,
            order=child_delivery_order_internal,
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.completed.value,
            supplied_inventory_item=inventory_item_child,
        )
        list_response = self.client.get(
            self.base_url,
            {"origin": self.origin.external_id, "include_children": "false"},
            format="json",
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(
            list_response.data["results"][0]["id"],
            str(supply_delivery_parent.external_id),
        )
        self.assertEqual(
            list_response.data["results"][0]["supplied_item_quantity"], "200.000000"
        )
        self.assertEqual(
            list_response.data["results"][0]["supplied_inventory_item"]["id"],
            str(self.inventory_item_origin.external_id),
        )
        self.assertEqual(
            list_response.data["results"][0]["supplied_inventory_item"]["net_content"],
            "300.000000",
        )

    def test_list_supply_delivery_as_superuser_with_request_order_filter(self):
        """Test listing supply deliveries as a superuser with request_order queryset filter"""
        self.client.force_authenticate(user=self.superuser)

        list_response = self.client.get(
            self.base_url,
            {"request_order": self.request_order_destination_external.external_id},
            format="json",
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(
            list_response.data["results"][0]["id"],
            str(self.purchase_order_destination.external_id),
        )
        self.assertEqual(
            list_response.data["results"][0]["status"],
            SupplyDeliveryStatusOptions.completed.value,
        )
        self.assertEqual(
            list_response.data["results"][0]["supplied_item_quantity"], "1500.000000"
        )

    def test_list_supply_delivery_as_user_with_permissions_with_request_order_filter(
        self,
    ):
        """Test listing supply deliveries as a user with permissions and request_order queryset filter"""
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            facility_organization=self.facility_organization,
            user=self.user,
            role=self.role,
        )
        list_response = self.client.get(
            self.base_url,
            {"request_order": self.request_order_destination_external.external_id},
            format="json",
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(
            list_response.data["results"][0]["id"],
            str(self.purchase_order_destination.external_id),
        )
        self.assertEqual(
            list_response.data["results"][0]["status"],
            SupplyDeliveryStatusOptions.completed.value,
        )
        self.assertEqual(
            list_response.data["results"][0]["supplied_item_quantity"], "1500.000000"
        )

    def test_list_supply_delivery_as_user_without_permissions_with_request_order_filter(
        self,
    ):
        """Test listing supply deliveries as a user without permissions and request_order queryset filter"""
        self.client.force_authenticate(user=self.user)

        list_response = self.client.get(
            self.base_url,
            {"request_order": self.request_order_destination_external.external_id},
            format="json",
        )
        self.assertEqual(list_response.status_code, 403)
        self.assertContains(
            list_response, "Cannot read supply requests", status_code=403
        )

    # Testcases for retrieve delivery orders

    def test_retrieve_delivery_order_as_superuser_with_request_order_filter(self):
        """
        Test retrieving a delivery order as a superuser with request_order filter
        """
        self.client.force_authenticate(user=self.superuser)
        get_response = self.client.get(
            self.delivery_orders_url,
            {
                "request_order": self.request_order_destination_external.external_id,
            },
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["results"][0]["id"],
            str(self.delivery_order_destination_external.external_id),
        )

    def test_retrieve_delivery_order_as_user_with_permissions_with_request_order_filter(
        self,
    ):
        """
        Test retrieving a delivery order as a user with permissions and request_order filter
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            facility_organization=self.facility_organization,
            user=self.user,
            role=self.role,
        )
        get_response = self.client.get(
            self.delivery_orders_url,
            {
                "request_order": self.request_order_destination_external.external_id,
            },
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["results"][0]["id"],
            str(self.delivery_order_destination_external.external_id),
        )

    def test_retrieve_delivery_order_as_user_without_permissions_with_request_order_filter(
        self,
    ):
        """
        Test retrieving a delivery order as a user without permissions and request_order filter
        """
        self.client.force_authenticate(user=self.user)
        get_response = self.client.get(
            self.delivery_orders_url,
            {
                "request_order": self.request_order_destination_external.external_id,
            },
            format="json",
        )
        self.assertEqual(get_response.status_code, 403)
        self.assertContains(
            get_response, "Cannot read supply requests", status_code=403
        )

    def test_retrieve_delivery_order_as_superuser_without_filter(self):
        """
        Test retrieving a delivery order as a superuser without filter
        """
        self.client.force_authenticate(user=self.superuser)
        get_response = self.client.get(self.delivery_orders_url, format="json")
        self.assertEqual(get_response.status_code, 400)
        self.assertContains(get_response, "No filters provided", status_code=400)

    def test_retrieve_delivery_order_as_superuser_without_request_order_filter(self):
        """
        Test retrieving a delivery order as a superuser without request_order filter
        """
        self.client.force_authenticate(user=self.superuser)
        get_response = self.client.get(
            self.delivery_orders_url,
            {
                "order": self.delivery_order_destination_external.external_id,
            },
            format="json",
        )
        self.assertEqual(get_response.status_code, 400)
        self.assertContains(get_response, "request_order is required", status_code=400)

    def test_retrieve_delivery_order_as_user_with_permissions_with_order_filter(self):
        """
        Test retrieving a delivery order as a user with permissions and order filter
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            facility_organization=self.facility_organization,
            user=self.user,
            role=self.role,
        )
        get_response = self.client.get(
            self.delivery_orders_url,
            {
                "request_order": self.request_order_destination_external.external_id,
                "order": self.delivery_order_destination_external.external_id,
            },
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["results"][0]["id"],
            str(self.delivery_order_destination_external.external_id),
        )

    def test_retrieve_delivery_order_as_user_without_permissions_with_order_filter(
        self,
    ):
        """
        Test retrieving a delivery order as a user without permissions and order filter
        """
        self.client.force_authenticate(user=self.user)
        get_response = self.client.get(
            self.delivery_orders_url,
            {
                "request_order": self.request_order_destination_external.external_id,
                "order": self.delivery_order_destination_external.external_id,
            },
            format="json",
        )
        self.assertEqual(get_response.status_code, 403)
        self.assertContains(
            get_response, "Cannot read supply requests", status_code=403
        )

    def test_retrieve_delivery_order_as_user_with_permissions_with_origin_filter(self):
        """
        Test retrieving a delivery order as a user with permissions with origin filter
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
            supplied_item_quantity=Decimal(200),
            supply_request=self.supply_request_internal.external_id,
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

        get_response = self.client.get(
            self.delivery_orders_url,
            {
                "request_order": self.request_order_internal.external_id,
                "origin": self.origin.external_id,
            },
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["results"][0]["id"],
            str(self.delivery_order_internal.external_id),
        )

    def test_retrieve_delivery_order_as_user_without_permissions_with_origin_filter(
        self,
    ):
        """
        Test retrieving a delivery order as a user without permissions with origin filter
        """
        self.client.force_authenticate(user=self.user)
        get_response = self.client.get(
            self.delivery_orders_url,
            {
                "request_order": self.request_order_internal.external_id,
                "origin": self.origin.external_id,
            },
            format="json",
        )
        self.assertEqual(get_response.status_code, 403)
        self.assertContains(
            get_response, "Cannot read supply requests", status_code=403
        )

    def test_retrieve_delivery_order_as_superuser_with_destination_filter(self):
        """
        Test retrieving a delivery order as a superuser with destination filter
        """
        self.client.force_authenticate(user=self.superuser)
        get_response = self.client.get(
            self.delivery_orders_url,
            {
                "request_order": self.request_order_destination_external.external_id,
                "destination": self.destination.external_id,
            },
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["results"][0]["id"],
            str(self.delivery_order_destination_external.external_id),
        )

    def test_retrieve_delivery_order_as_user_with_permissions_with_destination_filter(
        self,
    ):
        """
        Test retrieving a delivery order as a user with permissions with destination filter
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            facility_organization=self.facility_organization,
            user=self.user,
            role=self.role,
        )
        get_response = self.client.get(
            self.delivery_orders_url,
            {
                "request_order": self.request_order_destination_external.external_id,
                "destination": self.destination.external_id,
            },
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["results"][0]["id"],
            str(self.delivery_order_destination_external.external_id),
        )

    def test_retrieve_delivery_order_as_user_without_permissions_with_destination_filter(
        self,
    ):
        """
        Test retrieving a delivery order as a user without permissions with destination filter
        """
        self.client.force_authenticate(user=self.user)
        get_response = self.client.get(
            self.delivery_orders_url,
            {
                "request_order": self.request_order_destination_external.external_id,
                "destination": self.destination.external_id,
            },
            format="json",
        )
        self.assertEqual(get_response.status_code, 403)
        self.assertContains(
            get_response, "Cannot read supply requests", status_code=403
        )

    # Testcases for filtering supply deliveries

    def test_filter_supply_delivery_by_status_as_superuser(self):
        """
        Test filtering supply deliveries by status as a superuser
        """
        self.client.force_authenticate(user=self.superuser)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=500,
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        response = self.client.get(
            self.base_url,
            {
                "status": SupplyDeliveryStatusOptions.in_progress.value,
                "order": self.delivery_order_destination_external.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(supply_delivery.external_id)
        )
        self.assertEqual(
            response.data["results"][0]["status"],
            SupplyDeliveryStatusOptions.in_progress.value,
        )

    def test_filter_supply_delivery_by_status_as_user_with_permissions(self):
        """
        Test filtering supply deliveries by status as a user with permissions
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            facility_organization=self.facility_organization,
            user=self.user,
            role=self.role,
        )
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=Decimal(500),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        response = self.client.get(
            self.base_url,
            {
                "status": SupplyDeliveryStatusOptions.in_progress.value,
                "order": self.delivery_order_destination_external.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(supply_delivery.external_id)
        )
        self.assertEqual(
            response.data["results"][0]["status"],
            SupplyDeliveryStatusOptions.in_progress.value,
        )

    def test_filter_supply_delivery_by_status_as_user_without_permissions(self):
        """
        Test filtering supply deliveries by status as a user without permissions
        """
        self.client.force_authenticate(user=self.user)
        self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=Decimal(500),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        response = self.client.get(
            self.base_url,
            {
                "status": SupplyDeliveryStatusOptions.in_progress.value,
                "order": self.delivery_order_destination_external.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Cannot read supply requests", status_code=403)

    def test_filter_supply_delivery_as_superuser_without_queryset_filter(self):
        """
        Test filtering supply deliveries as a superuser without any queryset filter
        """
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.base_url,
            {"status": SupplyDeliveryStatusOptions.in_progress.value},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "No filters provided", status_code=400)

    def test_filter_supply_delivery_as_superuser_with_supplied_item_filter(self):
        """
        Test filtering supply deliveries as a superuser with supplied_item filter
        """
        self.client.force_authenticate(user=self.superuser)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=Decimal(500),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        response = self.client.get(
            self.base_url,
            {
                "status": SupplyDeliveryStatusOptions.in_progress.value,
                "supplied_item": self.product.external_id,
                "order": self.delivery_order_destination_external.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(supply_delivery.external_id)
        )
        self.assertEqual(
            response.data["results"][0]["status"],
            SupplyDeliveryStatusOptions.in_progress.value,
        )
        self.assertEqual(
            response.data["results"][0]["supplied_item"]["id"],
            str(self.product.external_id),
        )

    def test_filter_supply_delivery_as_superuser_with_supplied_inventory_item_product_knowledge(
        self,
    ):
        """
        Test filtering supply deliveries as a superuser with filtering by product knowledge from product of supplied_inventory_item
        """
        self.client.force_authenticate(user=self.superuser)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=Decimal(500),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        response = self.client.get(
            self.base_url,
            {
                "status": SupplyDeliveryStatusOptions.in_progress.value,
                "supplied_inventory_item_product_knowledge": self.product_knowledge.external_id,
                "order": self.delivery_order_destination_external.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(supply_delivery.external_id)
        )
        self.assertEqual(
            response.data["results"][0]["status"],
            SupplyDeliveryStatusOptions.in_progress.value,
        )
        self.assertEqual(
            response.data["results"][0]["supplied_inventory_item"]["id"],
            str(self.inventory_item_destination.external_id),
        )

    def test_filter_supply_delivery_as_superuser_with_supplied_item(self):
        """
        Test filtering supply deliveries as a superuser with filtering by supplied_item(product)
        """
        self.client.force_authenticate(user=self.superuser)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=Decimal(500),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        response = self.client.get(
            self.base_url,
            {
                "status": SupplyDeliveryStatusOptions.in_progress.value,
                "supplied_item": self.product.external_id,
                "order": self.delivery_order_destination_external.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(supply_delivery.external_id)
        )
        self.assertEqual(
            response.data["results"][0]["status"],
            SupplyDeliveryStatusOptions.in_progress.value,
        )
        self.assertEqual(
            response.data["results"][0]["supplied_item"]["id"],
            str(self.product.external_id),
        )

    def test_filter_supply_delivery_as_superuser_with_supplied_item_product_knowledge(
        self,
    ):
        """
        Test filtering supply deliveries as a superuser with filtering by product knowledge from supplied_item(product)
        """
        self.client.force_authenticate(user=self.superuser)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=Decimal(500),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        response = self.client.get(
            self.base_url,
            {
                "status": SupplyDeliveryStatusOptions.in_progress.value,
                "supplied_item_product_knowledge": self.product_knowledge.external_id,
                "order": self.delivery_order_destination_external.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(supply_delivery.external_id)
        )
        self.assertEqual(
            response.data["results"][0]["status"],
            SupplyDeliveryStatusOptions.in_progress.value,
        )
        self.assertEqual(
            response.data["results"][0]["supplied_item"]["id"],
            str(self.product.external_id),
        )

    def test_filter_supply_delivery_as_superuser_with_supply_request_filter(self):
        """
        Test filtering supply deliveries as a superuser with filtering by supply_request
        """
        self.client.force_authenticate(user=self.superuser)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=Decimal(500),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_destination,
            supply_request=self.supply_request_destination_external,
        )
        response = self.client.get(
            self.base_url,
            {
                "status": SupplyDeliveryStatusOptions.in_progress.value,
                "supply_request": self.supply_request_destination_external.external_id,
                "order": self.delivery_order_destination_external.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(supply_delivery.external_id)
        )
        self.assertEqual(
            response.data["results"][0]["status"],
            SupplyDeliveryStatusOptions.in_progress.value,
        )
        self.assertEqual(
            response.data["results"][0]["supplied_item"]["id"],
            str(self.product.external_id),
        )

    def test_filter_supply_delivery_as_superuser_with_origin_is_null_filter(self):
        """
        Test filtering supply deliveries as a superuser with filtering by origin is null
        """
        self.client.force_authenticate(user=self.superuser)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=Decimal(500),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        response = self.client.get(
            self.base_url,
            {
                "status": SupplyDeliveryStatusOptions.in_progress.value,
                "origin_is_null": "true",
                "order": self.delivery_order_destination_external.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(supply_delivery.external_id)
        )
        self.assertEqual(
            response.data["results"][0]["status"],
            SupplyDeliveryStatusOptions.in_progress.value,
        )
        self.assertEqual(
            response.data["results"][0]["supplied_item"]["id"],
            str(self.product.external_id),
        )

    def test_filter_supply_delivery_as_superuser_with_supplier_filter(self):
        """
        Test filtering supply deliveries as a superuser with filtering by supplier
        """
        self.client.force_authenticate(user=self.superuser)
        supply_delivery = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=Decimal(500),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.in_progress.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        response = self.client.get(
            self.base_url,
            {
                "status": SupplyDeliveryStatusOptions.in_progress.value,
                "supplier": self.supplier.external_id,
                "order": self.delivery_order_destination_external.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(supply_delivery.external_id)
        )
        self.assertEqual(
            response.data["results"][0]["status"],
            SupplyDeliveryStatusOptions.in_progress.value,
        )
        self.assertEqual(
            response.data["results"][0]["supplied_item"]["id"],
            str(self.product.external_id),
        )
