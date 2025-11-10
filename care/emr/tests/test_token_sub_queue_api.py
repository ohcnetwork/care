from django.urls import reverse
from model_bakery import baker

from care.emr.models.scheduling.token import (
    Token,
    TokenSubQueue,
)
from care.emr.resources.scheduling.token.spec import SchedulableResourceTypeOptions
from care.emr.resources.scheduling.token_sub_queue.spec import (
    TokenSubQueueStatusOptions,
)
from care.security.permissions.token import TokenPermissions
from care.utils.tests.base import CareAPITestBase


class TokenSubQueueAPITestCase(CareAPITestBase):
    """
    Test cases for TokenSubQueue API endpoints

    required fields:
    - resource_type eg: practitioner
    - resource_id eg: UUID of the practitioner

    """

    def setUp(self):
        self.user = self.create_user(username="testuser")
        self.superuser = self.create_super_user(username="superuser")
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, org_type="root"
        )
        self.superuser_resource = self.create_schedule_resource(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.superuser,
        )
        self.patient = self.create_patient()
        self.role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
                TokenPermissions.can_write_token.name,
            ],
        )
        self.base_url = reverse(
            "token-sub-queue-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def generate_token_sub_detail_url(self, facility_external_id, external_id):
        return reverse(
            "token-sub-queue-detail",
            kwargs={
                "facility_external_id": facility_external_id,
                "external_id": external_id,
            },
        )

    def create_token(self, facility, **kwargs):
        return baker.make(Token, facility=facility, **kwargs)

    def create_token_sub_queue(self, facility, **kwargs):
        return baker.make(TokenSubQueue, facility=facility, **kwargs)

    def create_schedule_resource(self, **kwargs):
        return baker.make("emr.SchedulableResource", **kwargs)

    def generate_token_queue_data(self, **kwargs):
        data = {
            "name": kwargs.get("name") or "OP Room 1",
            "status": kwargs.get("status") or TokenSubQueueStatusOptions.active.value,
            "resource_type": kwargs.get("resource_type")
            or SchedulableResourceTypeOptions.practitioner.value,
            "resource_id": kwargs.get("resource_id") or str(self.superuser.external_id),
        }
        data.update(kwargs)
        return data
