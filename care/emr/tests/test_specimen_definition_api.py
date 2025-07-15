from django.urls import reverse
from model_bakery import baker

from care.emr.resources.specimen_definition.spec import (
    PreferenceOptions,
    SpecimenDefinitionStatusOptions,
)
from care.utils.tests.base import CareAPITestBase


class SpecimenDefinitionAPITest(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="test-user")
        self.superuser = self.create_super_user(username="test-superuser")
        self.facility = self.create_facility(user=self.superuser, name="test-facility")
        self.facility_organization = self.create_facility_organization(
            name="test-facility-organization",
            facility=self.facility,
        )
        self.facility_location = baker.make(
            "emr.FacilityLocation",
            facility=self.facility,
            name="test-facility-location",
        )
        self.specimen_definition_data = {
            "slug": "test-specimen-definition",
            "title": "Test Specimen Definition",
            "status": SpecimenDefinitionStatusOptions.active,
            "description": "This is a test specimen definition.",
            "type_collected": {"code": "blood", "display": "Blood"},
            "patient_preparation": [{"code": "fasting", "display": "Fasting"}],
            "collection": {"code": "venipuncture", "display": "Venipuncture"},
            "type_tested": {
                "is_derived": False,
                "preference": PreferenceOptions.preferred,
                "container": None,
                "requirement": None,
                "retention_time": None,
                "single_use": None,
            },
        }

        self.base_url = reverse(
            "specimen_definition-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def get_detail_url(self, external_id):
        self.detail_url = reverse(
            "specimen_definition-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": external_id,
            },
        )

    def create_specimen_definition(self):
        return baker.make(
            "emr.SpecimenDefinition",
            facility=self.facility,
            slug="test-specimen-definition",
            title="Test Specimen Definition",
            status=SpecimenDefinitionStatusOptions.active,
            description="This is a test specimen definition.",
            type_collected={"code": "blood", "display": "Blood"},
            patient_preparation=[{"code": "fasting", "display": "Fasting"}],
            collection={
                "procedure": {"code": "venipuncture", "display": "Venipuncture"}
            },
            type_tested={"code": "cbc", "display": "Complete Blood Count"},
        )
