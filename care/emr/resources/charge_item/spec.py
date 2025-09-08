from enum import Enum

from django.shortcuts import get_object_or_404
from pydantic import UUID4, BaseModel, model_validator

from care.emr.models.account import Account
from care.emr.models.charge_item import ChargeItem
from care.emr.models.encounter import Encounter
from care.emr.models.patient import Patient
from care.emr.resources.base import EMRResource
from care.emr.resources.charge_item_definition.spec import ChargeItemDefinitionReadSpec
from care.emr.resources.common.coding import Coding
from care.emr.resources.common.monetary_component import (
    MonetaryComponent,
    MonetaryComponentType,
)
from care.emr.tagging.base import SingleFacilityTagManager


class ChargeItemStatusOptions(str, Enum):
    planned = "planned"
    billable = "billable"
    not_billable = "not_billable"
    aborted = "aborted"
    billed = "billed"
    paid = "paid"
    entered_in_error = "entered_in_error"


CHARGE_ITEM_CANCELLED_STATUS = [
    ChargeItemStatusOptions.entered_in_error.value,
    ChargeItemStatusOptions.not_billable.value,
    ChargeItemStatusOptions.aborted.value,
]


class ChargeItemResourceOptions(str, Enum):
    service_request = "service_request"
    medication_dispense = "medication_dispense"
    appointment = "appointment"
    bed_association = "bed_association"


class ChargeItemOverrideReason(BaseModel):
    text: str
    code: Coding | None = None


class ChargeItemSpec(EMRResource):
    """Base model for ChargeItem"""

    __model__ = ChargeItem
    __exclude__ = ["encounter", "account"]

    id: UUID4 | None = None
    title: str
    description: str | None = None
    status: ChargeItemStatusOptions
    code: Coding | None = None
    quantity: float
    unit_price_components: list[MonetaryComponent]
    note: str | None = None
    override_reason: ChargeItemOverrideReason | None = None

    @model_validator(mode="after")
    def check_duplicate_codes(self):
        codes = [
            component.code.code
            for component in self.unit_price_components
            if component.code
        ]
        if len(codes) != len(set(codes)):
            raise ValueError("Duplicate codes are not allowed.")
        return self

    @model_validator(mode="after")
    def check_single_base_component(self):
        component_types = [
            component.monetary_component_type
            for component in self.unit_price_components
        ]
        if component_types.count(MonetaryComponentType.base) > 1:
            raise ValueError("Only one base component is allowed.")
        return self

    @model_validator(mode="after")
    def validate_monetary_codes(self):
        # Validate that the codes used in the components are defined
        # in the facility or in the instance level
        # TODO
        return self


class ChargeItemWriteSpec(ChargeItemSpec):
    encounter: UUID4 | None = None
    patient: UUID4 | None = None
    account: UUID4 | None = None
    service_resource: ChargeItemResourceOptions | None = None
    service_resource_id: str | None = None

    @model_validator(mode="after")
    def validate_service_resource(self):
        if self.service_resource and not self.service_resource_id:
            raise ValueError("Service resource id is required.")
        return self

    @model_validator(mode="after")
    def validate_encounter_patient(self):
        if not self.encounter and not self.patient:
            raise ValueError("Encounter or patient is required")
        return self

    def perform_extra_deserialization(self, is_update, obj):
        if self.encounter:
            obj.encounter = get_object_or_404(Encounter, external_id=self.encounter)
            obj.patient = obj.encounter.patient
        if self.patient:
            obj.patient = get_object_or_404(Patient, external_id=self.patient)
        if self.account:
            obj.account = Account.objects.get(external_id=self.account)


class ChargeItemReadSpec(ChargeItemSpec):
    """Account read specification"""

    total_price_components: list[dict]
    total_price: float
    charge_item_definition: dict
    paid_invoice: dict | None = None
    tags: list[dict] = []
    service_resource: ChargeItemResourceOptions | None = None
    service_resource_id: str | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        from care.emr.resources.invoice.spec import InvoiceReadSpec

        mapping["id"] = obj.external_id
        if obj.charge_item_definition:
            mapping["charge_item_definition"] = ChargeItemDefinitionReadSpec.serialize(
                obj.charge_item_definition
            ).to_json()
        if obj.paid_invoice:
            mapping["paid_invoice"] = InvoiceReadSpec.serialize(
                obj.paid_invoice
            ).to_json()
        mapping["tags"] = SingleFacilityTagManager().render_tags(obj)
