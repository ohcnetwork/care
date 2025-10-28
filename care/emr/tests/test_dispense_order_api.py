from django.urls import reverse
from model_bakery import baker

from care.emr.resources.medication.dispense.dispense_order import (
    MedicationDispenseOrderStatusOptions,
)
from care.security.permissions.medication import MedicationPermissions
from care.security.permissions.supply_delivery import SupplyDeliveryPermissions
from care.utils.tests.base import CareAPITestBase


class DispenseOrderAPITestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.superuser = self.create_super_user(username="superuser")
        self.user = self.create_user(username="testuser")
        self.patient = self.create_patient()
        self.facility = self.create_facility(user=self.superuser, name="Test Facility")
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, name="Test Org"
        )
        self.location = self.create_facility_location(self.facility, name="Pharmacy")

        self.dispense_order_data = {
            "status": MedicationDispenseOrderStatusOptions.draft,
            "name": "Dispense Order",
            "note": "This is a test dispense order",
            "patient": str(self.patient.external_id),
            "location": str(self.location.external_id),
        }
        self.role = self.create_role_with_permissions(
            permissions=[
                SupplyDeliveryPermissions.can_read_supply_delivery.name,
                SupplyDeliveryPermissions.can_write_supply_delivery.name,
            ]
        )
        self.pharmacist_role = self.create_role_with_permissions(
            permissions=[
                MedicationPermissions.is_pharmacist.name,
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
            "dispense_order-list",
            kwargs={"facility_external_id": str(facility_external_id)},
        )

    def get_detail_url(self, facility_external_id, dispense_order_external_id):
        return reverse(
            "dispense_order-detail",
            kwargs={
                "facility_external_id": str(facility_external_id),
                "external_id": str(dispense_order_external_id),
            },
        )
