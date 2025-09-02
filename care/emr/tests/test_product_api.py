import datetime

from django.urls import reverse
from model_bakery import baker

from care.emr.resources.inventory.product.spec import ProductBatch, ProductStatusOptions
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

    def create_charge_item_definition(self, facility, **kwargs):
        return baker.make("emr.ChargeItemDefinition", **kwargs)

    def get_details_url(self, product=None):
        return reverse(
            "product-detail",
            kwargs={
                "external_id": product,
            },
        )

    def get_base_url(self):
        return reverse("product-list")

    def product_data(self):
        return {
            "status": ProductStatusOptions.active.value,
            "batch": ProductBatch.lot_number.value,
            "expiration_date": datetime.datetime.now(datetime.UTC)
            + datetime.timedelta(days=30),
        }
