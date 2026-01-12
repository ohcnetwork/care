import datetime
from decimal import Decimal
from enum import Enum

from django.conf import settings
from jsonschema import validate
from pydantic import UUID4, field_validator

from care.emr.models import Account
from care.emr.models.patient import Patient
from care.emr.resources.base import EMRResource, PeriodSpec
from care.emr.resources.patient.spec import PatientListSpec, PatientRetrieveSpec
from care.emr.tagging.base import SingleFacilityTagManager
from care.utils.shortcuts import get_object_or_404


class AccountStatusOptions(str, Enum):
    active = "active"
    inactive = "inactive"
    entered_in_error = "entered_in_error"
    on_hold = "on_hold"


class AccountBillingStatusOptions(str, Enum):
    open = "open"
    carecomplete_notbilled = "carecomplete_notbilled"
    billing = "billing"
    closed_baddebt = "closed_baddebt"
    closed_voided = "closed_voided"
    closed_completed = "closed_completed"
    closed_combined = "closed_combined"


class AccountSpec(EMRResource):
    """Base model for Account"""

    __model__ = Account
    __exclude__ = ["patient"]

    id: UUID4 | None = None
    status: AccountStatusOptions
    billing_status: AccountBillingStatusOptions
    name: str
    service_period: PeriodSpec
    description: str | None = None
    extensions: dict

    @field_validator("extensions")
    @classmethod
    def validate_extensions(cls, v):
        try:
            validate(v, settings.ACCOUNT_EXTENSIONS_JSON_SCHEMA)
        except Exception as e:
            raise ValueError("Invalid additional metadata") from e
        return v


class AccountCreateSpec(AccountSpec):
    """Account create specification"""

    patient: UUID4

    def perform_extra_deserialization(self, is_update, obj):
        obj.patient = get_object_or_404(Patient, external_id=self.patient)


class AccountMinimalReadSpec(AccountSpec):
    """Account read specification"""

    total_net: Decimal
    total_gross: Decimal
    total_paid: Decimal
    total_balance: Decimal
    total_billable_charge_items: Decimal
    calculated_at: datetime.datetime
    created_date: datetime.datetime
    modified_date: datetime.datetime

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id


class AccountReadSpec(AccountMinimalReadSpec):
    """Account read specification"""

    patient: dict
    tags: list[dict] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        mapping["patient"] = PatientListSpec.serialize(obj.patient).to_json()
        mapping["tags"] = SingleFacilityTagManager().render_tags(obj)


class AccountRetrieveSpec(AccountMinimalReadSpec):
    """Account retrieve specification"""

    patient: dict
    cached_items: list = []
    total_price_components: dict

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        mapping["patient"] = PatientRetrieveSpec.serialize(
            obj.patient, facility=obj.facility
        ).to_json()
