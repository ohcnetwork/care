from django.urls import reverse
from model_bakery import baker

from care.emr.resources.inventory.supply_delivery.delivery_order import (
    SupplyDeliveryOrderStatusOptions,
)
from care.security.permissions.supply_delivery import SupplyDeliveryPermissions
from care.utils.tests.base import CareAPITestBase


class DeliveryOrderAPITest(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.superuser = self.create_super_user(username="superuser")
        self.user = self.create_user(username="testuser")
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility,
        )
        self.supplier = self.create_organization(name="Test Supplier")
        self.destination = self.create_facility_location(facility=self.facility)
        self.origin = self.create_facility_location(facility=self.facility)
        self.role = self.create_role_with_permissions(
            permissions=[
                SupplyDeliveryPermissions.can_read_supply_delivery.name,
                SupplyDeliveryPermissions.can_write_supply_delivery.name,
            ]
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

    def generate_base_url(self, facility_external_id):
        return reverse(
            "delivery-order-list",
            kwargs={"facility_external_id": facility_external_id},
        )

    def generate_detail_url(self, external_id, facility_external_id):
        return reverse(
            "delivery-order-detail",
            kwargs={
                "external_id": external_id,
                "facility_external_id": facility_external_id,
            },
        )

    def create_delivery_order(self, **kwargs):
        return baker.make("emr.DeliveryOrder", **kwargs)

    def generate_delivery_order_data(self, status=None, **kwargs):
        data = {
            "name": "Test Delivery Order",
            "status": status or SupplyDeliveryOrderStatusOptions.draft.value,
            "note": "This is a test delivery order",
        }
        data.update(kwargs)
        return data
