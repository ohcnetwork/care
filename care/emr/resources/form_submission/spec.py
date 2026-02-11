import datetime
from enum import Enum

from pydantic import UUID4

from care.emr.models.encounter import Encounter
from care.emr.models.patient import Patient
from care.emr.models.questionnaire import FormSubmission, Questionnaire
from care.emr.resources.base import EMRResource
from care.emr.resources.user.spec import UserSpec
from care.utils.shortcuts import get_object_or_404


class FormSubmissionStatusChoices(str, Enum):
    draft = "draft"
    submitted = "submitted"
    entered_in_error = "entered_in_error"


class BaseFormSubmissionSpec(EMRResource):
    """Base model for form submission"""

    __model__ = FormSubmission

    id: UUID4 | None = None


class FormSubmissionUpdateSpec(BaseFormSubmissionSpec):
    """Form submission update specification"""

    status: FormSubmissionStatusChoices
    response_dump: dict


class FormSubmissionWriteSpec(FormSubmissionUpdateSpec):
    """Form submission write specification"""

    questionnaire: str
    patient: UUID4
    encounter: UUID4 | None = None

    def perform_extra_deserialization(self, is_update, obj):
        obj.questionnaire = get_object_or_404(Questionnaire, slug=self.questionnaire)
        obj.patient = get_object_or_404(Patient, external_id=self.patient)
        if self.encounter:
            obj.encounter = get_object_or_404(Encounter, external_id=self.encounter)
            obj.patient = obj.encounter.patient


class FormSubmissionReadSpec(FormSubmissionUpdateSpec):
    """Form submission read specification"""

    status: FormSubmissionStatusChoices
    response_dump: dict
    created_date: datetime.datetime
    modified_date: datetime.datetime | None = None

    created_by: UserSpec | None = None
    updated_by: UserSpec | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        cls.serialize_audit_users(mapping, obj)
