import datetime
from enum import Enum

from django.shortcuts import get_object_or_404
from pydantic import UUID4

from care.emr.models import Account
from care.emr.models.patient import Patient
from care.emr.resources.base import EMRResource, PeriodSpec
from care.emr.resources.patient.spec import PatientListSpec


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


class AccountCreateSpec(AccountSpec):
    """Account create specification"""

    patient: UUID4

    def perform_extra_deserialization(self, is_update, obj):
        obj.patient = get_object_or_404(Patient, external_id=self.patient)


class AccountReadSpec(AccountSpec):
    """Account read specification"""

    patient: dict
    total_net: float
    total_gross: float
    total_paid: float
    total_balance: float
    calculated_at: datetime.datetime
    created_date: datetime.datetime
    modified_date: datetime.datetime

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["patient"] = PatientListSpec.serialize(obj.patient)


class AccountRetrieveSpec(AccountReadSpec):
    """Account retrieve specification"""

    cached_items: list = []
    total_price_components: dict
