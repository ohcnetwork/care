from django.urls import reverse

from care.emr.resources.observation_definition.spec import (
    ObservationCategoryChoices,
    ObservationStatusChoices,
)
from care.security.permissions.observation_definition import (
    ObservationDefinitionPermissions,
)
from care.utils.tests.base import CareAPITestBase


class ObservationDefinitionAPITest(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="testuser")
        self.superuser = self.create_super_user(username="superuser")
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )

        self.role = self.create_role_with_permissions(
            permissions=[
                ObservationDefinitionPermissions.can_write_observation_definition.name,
                ObservationDefinitionPermissions.can_read_observation_definition.name,
            ],
        )
        self.observation_definition_data = {
            "title": "Blood Pressure",
            "slug": "blood-pressure",
            "category": ObservationCategoryChoices.vital_signs.value,
            "status": ObservationStatusChoices.active.value,
            "description": "Definition for measuring blood pressure",
            "code": {
                "system": "http://loinc.org",
                "code": "85354-9",
                "display": "Blood pressure panel with all children",
            },
            "facility": self.facility.external_id,
        }
        self.url = reverse("observation_definition-list")

    def get_detail_url(self, external_id):
        return reverse(
            "observation_definition-detail",
            kwargs={
                "external_id": external_id,
            },
        )
