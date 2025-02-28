# Not Being used
import datetime

from django.utils import timezone
from pydantic import UUID4, BaseModel

from care.emr.models import (
    Encounter,
    EncounterOrganization,
    FacilityLocationEncounter,
    TokenBooking,
)
from care.emr.models.patient import Patient
from care.emr.resources.base import EMRResource, PeriodSpec
from care.emr.resources.encounter.constants import (
    AdmitSourcesChoices,
    ClassChoices,
    DietPreferenceChoices,
    DischargeDispositionChoices,
    EncounterPriorityChoices,
    StatusChoices,
)
from care.emr.resources.facility.spec import FacilityBareMinimumSpec
from care.emr.resources.facility_organization.spec import FacilityOrganizationReadSpec
from care.emr.resources.location.spec import (
    FacilityLocationEncounterListSpecWithLocation,
    FacilityLocationListSpec,
)
from care.emr.resources.patient.spec import PatientListSpec
from care.emr.resources.scheduling.slot.spec import TokenBookingReadSpec
from care.facility.models import Facility


class HospitalizationSpec(BaseModel):
    re_admission: bool | None = None
    admit_source: AdmitSourcesChoices | None = None
    discharge_disposition: DischargeDispositionChoices | None = None
    diet_preference: DietPreferenceChoices | None = None


class EncounterSpecBase(EMRResource):
    __model__ = Encounter
    __exclude__ = [
        "patient",
        "organizations",
        "facility",
        "appointment",
        "current_location",
    ]

    id: UUID4 = None
    status: StatusChoices
    encounter_class: ClassChoices
    period: PeriodSpec = {}
    hospitalization: HospitalizationSpec | None = {}
    priority: EncounterPriorityChoices
    external_identifier: str | None = None


class EncounterCreateSpec(EncounterSpecBase):
    patient: UUID4
    facility: UUID4
    organizations: list[UUID4] = []
    appointment: UUID4 | None = None

    def perform_extra_deserialization(self, is_update, obj):
        if not is_update:
            obj.patient = Patient.objects.get(external_id=self.patient)
            obj.facility = Facility.objects.get(external_id=self.facility)
            if self.appointment:
                obj.appointment = TokenBooking.objects.get(external_id=self.appointment)
            obj._organizations = list(set(self.organizations))  # noqa SLF001
            obj.status_history = {
                "history": [{"status": obj.status, "moved_at": str(timezone.now())}]
            }
            obj.encounter_class_history = {
                "history": [
                    {"status": obj.encounter_class, "moved_at": str(timezone.now())}
                ]
            }


class EncounterUpdateSpec(EncounterSpecBase):
    def perform_extra_deserialization(self, is_update, obj):
        old_instance = Encounter.objects.get(id=obj.id)
        if old_instance.status != self.status:
            obj.status_history["history"].append(
                {"status": self.status, "moved_at": str(timezone.now())}
            )
        if old_instance.encounter_class != self.encounter_class:
            obj.encounter_class_history["history"].append(
                {"status": self.status, "moved_at": str(timezone.now())}
            )


class EncounterListSpec(EncounterSpecBase):
    patient: dict
    facility: dict
    status_history: dict
    encounter_class_history: dict
    created_date: datetime.datetime
    modified_date: datetime.datetime

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["patient"] = PatientListSpec.serialize(obj.patient).to_json()
        mapping["facility"] = FacilityBareMinimumSpec.serialize(obj.facility).to_json()


class EncounterRetrieveSpec(EncounterListSpec):
    appointment: dict = {}
    created_by: dict = {}
    updated_by: dict = {}
    organizations: list[dict] = []
    current_location: dict | None = None
    location_history: list[dict] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        if obj.appointment:
            mapping["appointment"] = TokenBookingReadSpec.serialize(
                obj.appointment
            ).to_json()
        organizations = EncounterOrganization.objects.filter(encounter=obj)
        mapping["organizations"] = [
            FacilityOrganizationReadSpec.serialize(encounter_org.organization).to_json()
            for encounter_org in organizations
        ]
        mapping["current_location"] = None
        if obj.current_location:
            mapping["current_location"] = FacilityLocationListSpec.serialize(
                obj.current_location
            ).to_json()
        mapping["location_history"] = [
            FacilityLocationEncounterListSpecWithLocation.serialize(i)
            for i in FacilityLocationEncounter.objects.filter(encounter=obj).order_by(
                "-created_date"
            )
        ]
        cls.serialize_audit_users(mapping, obj)
