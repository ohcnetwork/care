from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import UUID4, BaseModel, Field, model_validator
from rest_framework.exceptions import ValidationError

from care.emr.models.encounter import Encounter
from care.emr.models.inventory_item import InventoryItem
from care.emr.models.location import FacilityLocation
from care.emr.models.medication_dispense import DispenseOrder, MedicationDispense
from care.emr.models.medication_request import MedicationRequest
from care.emr.resources.base import EMRResource
from care.emr.resources.charge_item.spec import ChargeItemReadSpec
from care.emr.resources.inventory.inventory_item.spec import InventoryItemReadSpec
from care.emr.resources.location.spec import FacilityLocationListSpec
from care.emr.resources.medication.dispense.dispense_order import (
    MedicationDispenseOrderReadSpec,
    MedicationDispenseOrderStatusOptions,
)
from care.emr.resources.medication.request.spec import (
    DosageInstruction,
    MedicationRequestReadSpec,
)
from care.utils.shortcuts import get_object_or_404


class MedicationDispenseStatus(str, Enum):
    preparation = "preparation"
    in_progress = "in_progress"
    cancelled = "cancelled"
    on_hold = "on_hold"
    completed = "completed"
    entered_in_error = "entered_in_error"
    stopped = "stopped"
    declined = "declined"


MEDICATION_DISPENSE_CANCELLED_STATUSES = [
    MedicationDispenseStatus.cancelled.value,
    MedicationDispenseStatus.entered_in_error.value,
    MedicationDispenseStatus.stopped.value,
    MedicationDispenseStatus.declined.value,
]


class MedicationDispenseNotPerformedReason(str, Enum):
    outofstock = "outofstock"
    washout = "washout"
    surg = "surg"
    sintol = "sintol"
    sddi = "sddi"
    sdupther = "sdupther"
    saig = "saig"
    preg = "preg"


class MedicationDispenseCategory(str, Enum):
    inpatient = "inpatient"
    outpatient = "outpatient"
    community = "community"
    discharge = "discharge"


class SubstitutionType(str, Enum):
    E = "E"
    EC = "EC"
    BC = "BC"
    G = "G"
    TE = "TE"
    TB = "TB"
    TG = "TG"
    F = "F"
    N = "N"


class SubstitutionReason(str, Enum):
    CT = "CT"
    FP = "FP"
    OS = "OS"
    RR = "RR"


class MedicationDispenseSubstitution(BaseModel):
    was_substituted: bool
    substitution_type: SubstitutionType
    reason: SubstitutionReason


class BaseMedicationDispenseSpec(EMRResource):
    __model__ = MedicationDispense
    __exclude__ = [
        "patient",
        "encounter",
        "authorizing_request",
        "item",
        "location",
    ]
    id: UUID4 = None

    status: MedicationDispenseStatus
    not_performed_reason: MedicationDispenseNotPerformedReason | None = None
    category: MedicationDispenseCategory | None = None
    when_prepared: datetime | None = None
    when_handed_over: datetime | None = None
    note: str | None = None
    dosage_instruction: list[DosageInstruction] = []
    substitution: MedicationDispenseSubstitution | None = None


class CreateDispenseOrderStatusOptions(str, Enum):
    draft = "draft"
    in_progress = "in_progress"


class CreateDispenseOrder(BaseModel):
    name: str | None = None
    note: str | None = None
    alternate_identifier: str
    status: CreateDispenseOrderStatusOptions = CreateDispenseOrderStatusOptions.draft


class MedicationDispenseWriteSpec(BaseMedicationDispenseSpec):
    encounter: UUID4
    location: UUID4
    authorizing_request: UUID4 | None = None
    item: UUID4
    quantity: Decimal = Field(max_digits=20, decimal_places=0)
    days_supply: Decimal | None = Field(default=None, max_digits=20, decimal_places=0)
    fully_dispensed: bool | None = None
    order: UUID4 | None = None
    create_dispense_order: CreateDispenseOrder | None = None

    @model_validator(mode="after")
    def validate_prescription(self):
        if self.create_dispense_order and self.order:
            raise ValueError(
                "Cannot have both dispense order and create_dispense_order"
            )
        return self

    def perform_extra_deserialization(self, is_update, obj):
        obj.encounter = get_object_or_404(
            Encounter.objects.filter(external_id=self.encounter).only("id")
        )
        obj.patient = obj.encounter.patient
        if self.authorizing_request:
            obj.authorizing_request = get_object_or_404(
                MedicationRequest.objects.filter(
                    external_id=self.authorizing_request,
                    encounter=obj.encounter,
                ).only("id")
            )
        obj.location = get_object_or_404(
            FacilityLocation.objects.filter(
                external_id=self.location, facility=obj.encounter.facility
            ).only("id")
        )
        obj.item = get_object_or_404(
            InventoryItem.objects.filter(
                external_id=self.item, location__facility=obj.encounter.facility
            ).only("id")
        )
        obj._fully_dispensed = self.fully_dispensed  # noqa # SLF001
        if self.order:
            obj.order = get_object_or_404(
                DispenseOrder.objects.only("id").filter(external_id=self.order)
            )
        elif self.create_dispense_order is not None:
            dispense_order_obj = DispenseOrder.objects.filter(
                alternate_identifier=self.create_dispense_order.alternate_identifier,
                patient=obj.patient,
                location=obj.location,
            ).first()
            if dispense_order_obj and dispense_order_obj.status not in [
                MedicationDispenseOrderStatusOptions.draft.value,
                MedicationDispenseOrderStatusOptions.in_progress.value,
            ]:
                raise ValidationError("Prescription is not active")
            if not dispense_order_obj:
                user = self._context.get("user")
                dispense_order_obj = DispenseOrder.objects.create(
                    status=self.create_dispense_order.status,
                    alternate_identifier=self.create_dispense_order.alternate_identifier,
                    patient=obj.patient,
                    location=obj.location,
                    facility=obj.encounter.facility,
                    name=self.create_dispense_order.name,
                    note=self.create_dispense_order.note,
                    created_by=user,
                    updated_by=user,
                )
            obj.order = dispense_order_obj


class MedicationDispenseUpdateSpec(BaseMedicationDispenseSpec):
    fully_dispensed: bool | None = None
    order: UUID4 | None = None

    def perform_extra_deserialization(self, is_update, obj):
        obj._fully_dispensed = self.fully_dispensed  # noqa
        if self.order:
            obj.order = get_object_or_404(
                DispenseOrder.objects.only("id").filter(external_id=self.order)
            )


class MedicationDispenseReadSpec(BaseMedicationDispenseSpec):
    item: dict
    charge_item: dict | None = None
    created_date: datetime
    modified_date: datetime
    location: dict
    quantity: Decimal = Field(max_digits=20, decimal_places=0)
    authorizing_request: dict | None = None
    order: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["item"] = InventoryItemReadSpec.serialize(obj.item).to_json()
        if obj.charge_item:
            mapping["charge_item"] = ChargeItemReadSpec.serialize(
                obj.charge_item
            ).to_json()
        mapping["location"] = FacilityLocationListSpec.serialize(obj.location).to_json()
        if obj.authorizing_request:
            mapping["authorizing_request"] = MedicationRequestReadSpec.serialize(
                obj.authorizing_request
            ).to_json()
        if obj.order:
            mapping["order"] = MedicationDispenseOrderReadSpec.serialize(
                obj.order
            ).to_json()


class MedicationDispenseRetrieveSpec(MedicationDispenseReadSpec):
    pass
