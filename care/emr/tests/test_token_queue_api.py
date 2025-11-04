from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from care.emr.models.scheduling.token import (
    TokenQueue,
)
from care.emr.resources.scheduling.token.spec import SchedulableResourceTypeOptions
from care.security.permissions.token import TokenPermissions
from care.utils.tests.base import CareAPITestBase


class TokenQueueAPITestCase(CareAPITestBase):
    def setUp(self):
        self.user = self.create_user(username="testuser")
        self.superuser = self.create_super_user(username="superuser")
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, org_type="root"
        )
        self.resource = self.create_schedule_resource(
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
            "token-queue-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def create_schedule_resource(self, **kwargs):
        return baker.make("emr.SchedulableResource", **kwargs)

    def generate_token_queue_data(self, **kwargs):
        """
        Generate data for creating a TokenQueue instance.

        fields:
        - resource_type: The type of schedulable resource type for the token queue.
        - resource_id: The external ID of the resource for the token queue.

        These fields are required to validate schedulable resource based on the resource type
        """
        data = {
            "name": "Test Token Queue",
            "date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            "resource_type": kwargs.get(
                "resource_type", SchedulableResourceTypeOptions.practitioner.value
            ),
            "resource_id": kwargs.get("resource_id", str(self.superuser.external_id)),
            "resource": kwargs.get("resource", str(self.resource.external_id)),
        }
        data.update(kwargs)
        return data

    def create_token_queue(self, facility, **kwargs):
        return baker.make(TokenQueue, facility=facility, **kwargs)
