import datetime
from enum import Enum

from pydantic import UUID4, model_validator
from rest_framework.generics import get_object_or_404

from care.emr.models import Patient
from care.emr.models.organization import FacilityOrganizationUser
from care.emr.models.resource_request import ResourceRequest, ResourceRequestComment
from care.emr.resources.base import EMRResource
from care.emr.resources.facility.spec import FacilityReadSpec
from care.emr.resources.patient.spec import PatientListSpec
from care.emr.resources.user.spec import UserSpec
from care.facility.models import Facility
from care.users.models import User


class StatusChoices(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"
    transportation_to_be_arranged = "transportation_to_be_arranged"
    transfer_in_progress = "transfer_in_progress"
    completed = "completed"


class CategoryChoices(str, Enum):
    patient_care = "patient_care"
    comfort_devices = "comfort_devices"
    medicines = "medicines"
    financial = "financial"
    supplies = "supplies"
    other = "other"


class ResourceRequestBaseSpec(EMRResource):
    __model__ = ResourceRequest
    __exclude__ = [
        "origin_facility",
        "approving_facility",
        "assigned_facility",
        "related_patient",
        "assigned_to",
    ]

    id: UUID4 | None = None
    emergency: bool
    title: str
    reason: str
    referring_facility_contact_name: str
    referring_facility_contact_number: str
    status: str
    category: str
    priority: int


class ResourceRequestCreateSpec(ResourceRequestBaseSpec):
    origin_facility: UUID4
    approving_facility: UUID4 | None = None
    assigned_facility: UUID4 | None = None
    related_patient: UUID4 | None = None
    assigned_to: UUID4 | None = None

    @model_validator(mode="after")
    def validate_assigned_to_user(self):
        if self.assigned_to:
            if not self.assigned_facility:
                raise ValueError(
                    "Assigned facility is required for assigning the request to a user"
                )

            if not FacilityOrganizationUser.objects.filter(
                organization__facility__external_id=self.assigned_facility,
                user__external_id=self.assigned_to,
            ).exists():
                raise ValueError(
                    "Assigned user is not a member of the assigned facility"
                )
        return self

    def perform_extra_deserialization(self, is_update, obj):
        if not is_update:
            obj.origin_facility = get_object_or_404(
                Facility, external_id=self.origin_facility
            )
        if self.approving_facility:
            obj.approving_facility = get_object_or_404(
                Facility, external_id=self.approving_facility
            )
        if self.assigned_facility:
            obj.assigned_facility = get_object_or_404(
                Facility, external_id=self.assigned_facility
            )
        if self.related_patient and not is_update:
            obj.related_patient = get_object_or_404(
                Patient, external_id=self.related_patient
            )
        if self.assigned_to:
            obj.assigned_to = get_object_or_404(User, external_id=self.assigned_to)


class ResourceRequestListSpec(ResourceRequestBaseSpec):
    origin_facility: dict
    assigned_facility: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = str(obj.external_id)
        mapping["origin_facility"] = FacilityReadSpec.serialize(
            obj.origin_facility
        ).to_json()
        if obj.assigned_facility:
            mapping["assigned_facility"] = FacilityReadSpec.serialize(
                obj.assigned_facility
            ).to_json()


class ResourceRequestRetrieveSpec(ResourceRequestBaseSpec):
    origin_facility: dict
    approving_facility: dict | None = None
    assigned_facility: dict | None = None
    related_patient: dict | None = None
    assigned_to: dict | None = None
    created_by: dict | None = None
    updated_by: dict | None = None
    created_date: datetime.datetime
    modified_date: datetime.datetime

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = str(obj.external_id)
        mapping["origin_facility"] = FacilityReadSpec.serialize(
            obj.origin_facility
        ).to_json()
        if obj.approving_facility:
            mapping["approving_facility"] = FacilityReadSpec.serialize(
                obj.approving_facility
            ).to_json()
        if obj.assigned_facility:
            mapping["assigned_facility"] = FacilityReadSpec.serialize(
                obj.assigned_facility
            ).to_json()
        if obj.related_patient:
            mapping["related_patient"] = PatientListSpec.serialize(
                obj.related_patient
            ).to_json()
        if obj.assigned_to:
            mapping["assigned_to"] = UserSpec.serialize(obj.assigned_to).to_json()

        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by)
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by)


class ResourceRequestCommentBaseSpec(EMRResource):
    __model__ = ResourceRequestComment
    __exclude__ = ["request"]

    comment: str


class ResourceRequestCommentCreateSpec(ResourceRequestCommentBaseSpec):
    pass


class ResourceRequestCommentListSpec(ResourceRequestCommentBaseSpec):
    created_by: dict | None = None
    created_date: datetime.datetime

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by)


class ResourceRequestCommentRetrieveSpec(ResourceRequestCommentListSpec):
    pass
