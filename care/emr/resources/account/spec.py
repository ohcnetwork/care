import datetime
from decimal import Decimal
from enum import Enum

from pydantic import UUID4, Field

from care.emr.extensions.base import ExtensionResource
from care.emr.extensions.validator import ExtensionValidator
from care.emr.models import Account
from care.emr.models.encounter import Encounter
from care.emr.models.patient import Patient
from care.emr.resources.base import EMRResource, PeriodSpec
from care.emr.resources.encounter.spec import EncounterRetrieveSpec
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
    ___extension_resource_type__ = ExtensionResource.account

    id: UUID4 | None = None
    status: AccountStatusOptions
    billing_status: AccountBillingStatusOptions
    name: str
    service_period: PeriodSpec
    description: str | None = None


class AccountCreateSpec(ExtensionValidator, AccountSpec):
    """Account create specification"""

    patient: UUID4

    def perform_extra_deserialization(self, is_update, obj):
        obj.patient = get_object_or_404(Patient, external_id=self.patient)


class AccountUpdateSpec(ExtensionValidator, AccountSpec):
    primary_encounter: UUID4 | None = None

    def perform_extra_deserialization(self, is_update, obj):
        if self.primary_encounter:
            obj.primary_encounter = get_object_or_404(
                Encounter, external_id=self.primary_encounter
            )


class AccountMinimalReadSpec(AccountSpec):
    """Account read specification"""

    total_gross: Decimal = Field(max_digits=20, decimal_places=6)
    total_paid: Decimal = Field(max_digits=20, decimal_places=6)
    total_balance: Decimal = Field(max_digits=20, decimal_places=6)
    total_billable_charge_items: Decimal = Field(max_digits=20, decimal_places=6)
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


class AccountRetrieveSpec(AccountReadSpec):
    """Account retrieve specification"""

    patient: dict
    primary_encounter: dict
    cached_items: list = []
    total_price_components: dict
    extensions: dict

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        if obj.primary_encounter:
            mapping["primary_encounter"] = EncounterRetrieveSpec.serialize(
                obj.primary_encounter
            ).to_json()
        mapping["patient"] = PatientRetrieveSpec.serialize(
            obj.patient, facility=obj.facility
        ).to_json()
