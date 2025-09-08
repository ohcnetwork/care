from datetime import date
from enum import Enum

from django.shortcuts import get_object_or_404
from pydantic import UUID4

from care.emr.models.patient import Patient
from care.emr.models.scheduling.token import Token, TokenCategory, TokenSubQueue
from care.emr.resources.base import EMRResource
from care.emr.resources.patient.spec import PatientListSpec
from care.emr.resources.scheduling.resource.spec import serialize_resource
from care.emr.resources.scheduling.schedule.spec import SchedulableResourceTypeOptions
from care.emr.resources.scheduling.token_category.spec import TokenCategoryReadSpec
from care.emr.resources.scheduling.token_queue.spec import TokenQueueReadSpec
from care.emr.resources.scheduling.token_sub_queue.spec import TokenSubQueueReadSpec
from care.emr.resources.user.spec import UserSpec


class TokenStatusOptions(str, Enum):
    UNFULFILLED = "UNFULFILLED"
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
    ENTERED_IN_ERROR = "ENTERED_IN_ERROR"


class TokenBaseSpec(EMRResource):
    __model__ = Token
    __exclude__ = []

    id: UUID4 | None = None


class TokenGenerateSpec(TokenBaseSpec):
    patient: UUID4 | None = None
    category: UUID4
    note: str | None = None
    sub_queue: UUID4 | None = None

    def perform_extra_deserialization(self, is_update, obj):
        if self.patient:
            obj.patient = get_object_or_404(Patient, external_id=self.patient)
        obj.category = get_object_or_404(TokenCategory, external_id=self.category)
        if self.sub_queue:
            obj.sub_queue = get_object_or_404(TokenSubQueue, external_id=self.sub_queue)


class TokenGenerateWithQueueSpec(TokenGenerateSpec):
    resource_type: SchedulableResourceTypeOptions
    resource_id: UUID4
    date: date


class TokenUpdateSpec(TokenBaseSpec):
    status: TokenStatusOptions | None = None
    note: str | None = None
    sub_queue: UUID4 | None = None

    def perform_extra_deserialization(self, is_update, obj):
        if self.sub_queue:
            obj.sub_queue = get_object_or_404(TokenSubQueue, external_id=self.sub_queue)


class TokenMinimalSpec(TokenBaseSpec):
    note: str
    number: int
    status: TokenStatusOptions


class TokenReadSpec(TokenBaseSpec):
    category: dict
    sub_queue: dict
    note: str
    patient: dict
    number: int
    status: TokenStatusOptions
    queue: TokenQueueReadSpec

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["category"] = TokenCategoryReadSpec.serialize(obj.category).to_json()
        mapping["queue"] = TokenQueueReadSpec.serialize(obj.queue).to_json()
        if obj.sub_queue:
            mapping["sub_queue"] = TokenSubQueueReadSpec.serialize(
                obj.sub_queue
            ).to_json()
        if obj.patient:
            mapping["patient"] = PatientListSpec.serialize(obj.patient).to_json()


class TokenRetrieveSpec(TokenReadSpec):
    created_by: UserSpec
    updated_by: UserSpec | None = None
    booking: dict
    resource_type: str
    resource: dict

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        from care.emr.resources.scheduling.slot.spec import TokenBookingMinimumReadSpec

        super().perform_extra_serialization(mapping, obj)
        cls.serialize_audit_users(mapping, obj)
        if obj.booking:
            mapping["booking"] = TokenBookingMinimumReadSpec.serialize(
                obj.booking
            ).to_json()
        mapping["resource_type"] = obj.queue.resource.resource_type
        mapping["resource"] = serialize_resource(obj.queue.resource)
