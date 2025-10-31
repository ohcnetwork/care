from django.urls import reverse
from model_bakery import baker

from care.emr.models.scheduling.token import (
    Token,
    TokenCategory,
    TokenQueue,
    TokenSubQueue,
)
from care.security.permissions.token import TokenPermissions
from care.utils.tests.base import CareAPITestBase


class TokenAPITests(CareAPITestBase):
    def setUp(self):
        self.user = self.create_user()
        self.superuser = self.create_super_user()
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.patient = self.create_patient()
        self.schedule_resource = self.create_schedule_resource(
            facility=self.facility, user=self.user
        )
        self.token_queue = self.create_queue(
            facility=self.facility, resource=self.schedule_resource
        )
        self.token_category = self.create_category(
            facility=self.facility, name="general"
        )

        self.token_url = self.generate_base_url(
            str(self.facility.external_id), str(self.token_queue.external_id)
        )

        self.role = self.create_role_with_permissions(
            permissions=[
                TokenPermissions.can_list_token.name,
                TokenPermissions.can_write_token.name,
            ]
        )

    def generate_base_url(self, facility, token_queue):
        return reverse(
            "queue-list",
            kwargs={
                "facility_external_id": facility,
                "token_queue_external_id": token_queue,
            },
        )

    def generate_detail_url(self, facility, external_id):
        return reverse(
            "queue-detail",
            kwargs={
                "facility_external_id": facility,
                "external_id": external_id,
            },
        )

    def generate_token_data(self, **kwargs):
        return {
            "patient": kwargs.get("patient"),
            "category": kwargs.get("category"),
            **kwargs,
        }

    def create_schedule_resource(self, **kwargs):
        return baker.make("emr.SchedulableResource", **kwargs)

    def create_token(self, **kwargs):
        data = self.generate_token_data(**kwargs)
        return baker.make(Token, **data)

    def create_category(self, **kwargs):
        return baker.make(TokenCategory, **kwargs)

    def create_queue(self, **kwargs):
        return baker.make(TokenQueue, **kwargs)

    def create_subqueue(self, **kwargs):
        return baker.make(TokenSubQueue, **kwargs)
