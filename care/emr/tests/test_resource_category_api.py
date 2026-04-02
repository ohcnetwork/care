from django.urls import reverse
from model_bakery import baker

from care.emr.models.resource_category import ResourceCategory
from care.security.permissions.resource_category import ResourceCategoryPermissions
from care.utils.tests.base import CareAPITestBase


class ResourceCategoryAPITestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.super_user = self.create_super_user()
        self.user = self.create_user()
        self.facility = self.create_facility(
            user=self.super_user,
        )
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, org_type="root"
        )
        self.premissions = [
            ResourceCategoryPermissions.can_write_resource_category.name,
            ResourceCategoryPermissions.can_read_resource_category.name,
        ]
        self.url = reverse(
            "resource_category-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def get_url(self, facility):
        return reverse(
            "resource_category-list",
            kwargs={"facility_external_id": facility.external_id},
        )

    def get_detail_url(self, facility, resource_category):
        return reverse(
            "resource_category-detail",
            kwargs={
                "facility_external_id": facility.external_id,
                "slug": resource_category.slug,
            },
        )

    def generate_resource_category_data(self, **kwargs):
        data = {
            "title": kwargs.get("title", "Test Resource Category"),
            "description": kwargs.get("description", "Test Description"),
            "slug_value": kwargs.get("slug_value", "test-resource-category"),
            "resource_type": kwargs.get("resource_type", "product_knowledge"),
            "resource_sub_type": kwargs.get("resource_sub_type", "other"),
            "facility": kwargs.get("facility", self.facility.external_id),
            **kwargs,
        }
        data.update(kwargs)
        return data

    def create_resource_category(self, **kwargs):
        return baker.make(ResourceCategory, facility=self.facility, **kwargs)
