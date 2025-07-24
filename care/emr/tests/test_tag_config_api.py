from django.urls import reverse
from model_bakery import baker

from care.emr.resources.tag.config_spec import (
    TagCategoryChoices,
    TagResource,
    TagStatus,
)
from care.utils.tests.base import CareAPITestBase


class TestTagConfigAPI(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="testuser")
        self.superuser = self.create_super_user(username="testsuperuser")
        self.facility = self.create_facility(name="Test Facility", user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, name="Test Facility Org"
        )
        self.organization = self.create_organization(
            name="Test Organization", user=self.superuser
        )
        self.base_url = reverse("tag_config-list")

    def generate_tag_config_data(
        self,
        facility=None,
        facility_organization=None,
        organization=None,
        status=None,
        category=None,
        resource=None,
        slug=None,
    ):
        return {
            "facility": facility or str(self.facility.external_id),
            "facility_organization": facility_organization
            or str(self.facility_organization.external_id),
            "organization": organization or str(self.organization.external_id),
            "status": status or TagStatus.active.value,
            "slug": slug or "test-tag",
            "display": "Test Tag",
            "description": "This is a test tag config",
            "category": category or TagCategoryChoices.clinical.value,
            "priority": 1,
            "resource": resource or TagResource.encounter.value,
        }

    def get_detail_url(self, external_id):
        return reverse("tag_config-detail", kwargs={"external_id": external_id})

    def create_tag_config(
        self,
        facility=None,
        facility_organization=None,
        organization=None,
        status=None,
        category=None,
        resource=None,
        slug=None,
    ):
        tag_config_data = self.generate_tag_config_data(
            facility=facility,
            facility_organization=facility_organization,
            organization=organization,
            status=status,
            category=category,
            resource=resource,
            slug=slug,
        )
        return baker.make("emr.TagConfig", **tag_config_data)
