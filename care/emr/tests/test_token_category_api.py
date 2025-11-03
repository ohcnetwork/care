from django.urls import reverse
from model_bakery import baker

from care.emr.models.scheduling.token import TokenCategory
from care.security.permissions.token import TokenPermissions
from care.utils.tests.base import CareAPITestBase


class TokenCategoryAPITestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.superuser = self.create_super_user()
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.patient = self.create_patient()
        self.role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token_category,
                TokenPermissions.can_write_token_category,
            ],
        )
        self.base_url = self.generate_category_url(
            facility=str(self.facility.external_id),
        )
        self.category_data = {
            "name": "General",
            "resource_type": "location",
            "shorthand": "GEN",
            "metadata": {"description": "General category"},
        }

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
