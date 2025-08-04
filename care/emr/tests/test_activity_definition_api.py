from django.urls import reverse
from model_bakery import baker

from care.emr.resources.activity_definition.spec import (
    ActivityDefinitionCategoryOptions,
    ActivityDefinitionKindOptions,
    ActivityDefinitionStatusOptions,
)
from care.security.permissions.activity_definition import ActivityDefinitionPermissions
from care.utils.tests.base import CareAPITestBase


class ActivityDefinitionAPITestBase(CareAPITestBase):
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
                ActivityDefinitionPermissions.can_read_activity_definition.name,
                ActivityDefinitionPermissions.can_write_activity_definition.name,
            ]
        )
        self.base_url = self.get_base_urlreverse(
            "activity_definition-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        self.facility_location = self.create_facility_location(
            facility=self.facility, name="Test Facility Location"
        )

    def generate_activity_definition_data(
        self, slug=None, title=None, status=None, category=None, kind=None, **kwargs
    ):
        return {
            "slug": slug or "test-activity-definition",
            "title": title or "Test Activity Definition",
            "derived_from_uri": None,
            "status": status or ActivityDefinitionStatusOptions.active.value,
            "description": "This is a test activity definition.",
            "usage": "Test usage",
            "category": category or ActivityDefinitionCategoryOptions.laboratory.value,
            "kind": kind or ActivityDefinitionKindOptions.service_request.value,
            "code": {"system": "http://example.com", "code": "12345"},
            "body_site": None,
            "diagnostic_report_codes": [],
            **kwargs,
        }

    def create_activity_definition(self, **kwargs):
        data = self.generate_activity_definition_data(**kwargs)
        return baker.make(
            "ActivityDefinition",
            **data,
            specimen_requirements=[self.generate_specimen_definition().id],
            observation_result_requirements=[self.generate_observation_definition().id],
            healthcare_service=self.generate_healthcare_service().id,
            charge_item_definitions=[self.charge_item_definition().id],
        )

    def get_details_url(self, facility=None, activity_definition=None):
        return reverse(
            "activity_definition-detail",
            kwargs={
                "facility_external_id": facility,
                "external_id": activity_definition,
            },
        )

    def get_base_url(self, facility=None):
        return reverse(
            "activity_definition-list",
            kwargs={"facility_external_id": facility},
        )

    def generate_specimen_definition(self, facility):
        return baker.make(
            "emr.SpecimenDefinition",
            slug="test-specimen-definition",
            title="Test Specimen Definition",
            description="This is a test specimen definition.",
            facility=facility,
        )

    def generate_observation_definition(self, facility):
        return baker.make(
            "emr.ObservationDefinition",
            slug="test-observation-definition",
            title="Test Observation Definition",
            description="This is a test observation definition.",
            facility=facility,
        )

    def generate_healthcare_service(self, facility):
        return baker.make(
            "emr.HealthcareService", name="Test Healthcare Service", facility=facility
        )

    def charge_item_definition(self, facility):
        return baker.make(
            "emr.ChargeItemDefinition",
            slug="test-charge-item-definition",
            title="Test Charge Item Definition",
            description="This is a test charge item definition.",
            facility=facility,
        )

    def create_facility_location(self, facility, **kwargs):
        return baker.make("emr.FacilityLocation", facility=facility, **kwargs)
