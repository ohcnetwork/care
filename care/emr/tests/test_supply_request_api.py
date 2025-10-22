from django.urls import reverse
from model_bakery import baker

from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.resources.inventory.supply_request.spec import SupplyRequestStatusOptions
from care.security.permissions.supply_request import SupplyRequestPermissions
from care.utils.tests.base import CareAPITestBase


class SupplyRequestAPITestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="testuser")
        self.superuser = self.create_super_user(username="superuser")
        self.patient = self.create_patient(name="Test Patient")
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility,
        )
        self.supplier = self.create_organization(name="Test Supplier")
        self.destination = self.create_facility_location(facility=self.facility)
        self.origin = self.create_facility_location(facility=self.facility)

        self.request_order = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )

        self.product_knowledge = baker.make(
            ProductKnowledge,
            facility=self.facility,
            slug=f"f-{self.facility.external_id}-product-knowledge",
        )

        self.base_url = reverse("supply_request-list")
        self.role = self.create_role_with_permissions(
            permissions=[
                SupplyRequestPermissions.can_write_supply_request,
                SupplyRequestPermissions.can_read_supply_request,
            ]
        )
        self.request_order_url = reverse("supply_request-request-orders")

    def generate_supply_request_data(self, quantity=None, **kwargs):
        data = {
            "status": SupplyRequestStatusOptions.active,
            "quantity": quantity or 100,
            "item": str(self.product_knowledge.external_id),
            **kwargs,
        }
        data.update(kwargs)
        return data

    def create_request_order(self, **kwargs):
        return baker.make("emr.RequestOrder", name="Test Request Order", **kwargs)

    def create_supply_request(self, **kwargs):
        return baker.make(
            "emr.SupplyRequest",
            status=SupplyRequestStatusOptions.active,
            item=self.product_knowledge,
            **kwargs,
        )

    def get_detail_url(self, external_id):
        return reverse("supply_request-detail", kwargs={"external_id": external_id})

    def create_facility_location(self, facility, **kwargs):
        from care.emr.models import FacilityLocation, FacilityLocationOrganization

        location = baker.make(FacilityLocation, facility=facility, **kwargs)
        baker.make(
            FacilityLocationOrganization,
            location=location,
            organization=self.facility_organization,
        )
        return location
