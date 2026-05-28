from types import SimpleNamespace

from django_filters import rest_framework as filters

from care.emr.models.encounter import Encounter, EncounterOrganization
from care.emr.models.tag_config import TagConfig
from care.emr.reports.context_builder.data_point_registry import DataPointRegistry
from care.emr.reports.context_builder.data_points.allergy_intolerance import (
    AllergyIntoleranceContextBuilder,
)
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
    SingleObjectContextBuilder,
)
from care.emr.reports.context_builder.data_points.diagnosis import (
    DiagnosisContextBuilder,
)
from care.emr.reports.context_builder.data_points.diagnostic_report import (
    DiagnosticReportContextBuilder,
)
from care.emr.reports.context_builder.data_points.facility import FacilityContextBuilder
from care.emr.reports.context_builder.data_points.medication import (
    MedicationPrescriptionContextBuilder,
)
from care.emr.reports.context_builder.data_points.patient import (
    IdentifiersContextBuilder,
    PatientMinimumContextBuilder,
    PatientTagContextBuilder,
    TagFilter,
)
from care.emr.reports.context_builder.data_points.questionnaire import (
    QuestionnaireContextBuilder,
)
from care.emr.reports.context_builder.data_points.service_request import (
    ServiceRequestBaseContextBuilder,
)
from care.emr.reports.context_builder.data_points.symptom import SymptomsContextBuilder
from care.emr.reports.context_builder.data_points.user import SingleUserIdContextBuilder

STATUS_DISPLAY = {
    "planned": "Planned",
    "in_progress": "In Progress",
    "completed": "Completed",
    "cancelled": "Cancelled",
    "entered_in_error": "Entered in Error",
}

ENCOUNTER_CLASS_DISPLAY = {
    "imp": "Inpatient",
    "amb": "Outpatient",
    "obsenc": "Observation",
    "emer": "Emergency",
    "vr": "Virtual",
    "hh": "Home Health",
}

ENCOUNTER_PRIORITY_DISPLAY = {
    "ASAP": "ASAP",
    "callback_results": "Callback Results",
    "callback_for_scheduling": "Callback for Scheduling",
    "elective": "Elective",
    "emergency": "Emergency",
    "preop": "Preop",
    "as_needed": "As Needed",
    "routine": "Routine",
    "rush_reporting": "Rush Reporting",
    "stat": "Stat",
    "timing_critical": "Timing Critical",
    "use_as_directed": "Use as Directed",
    "urgent": "Urgent",
}


class EncounterCareTeamContextBuilder(QuerysetContextBuilder):
    def get_context(self):
        return self.parent_context.care_team

    user = Field(
        display="User",
        target_context=SingleUserIdContextBuilder,
        preview_value="",
        description="User who is part of the encounter care team",
    )
    role = Field(
        display="Role",
        preview_value="Primary care physician",
        mapping=lambda c: c.role.get("display")
        if c.role and c.role.get("display")
        else "",
        description="Role of the user in the encounter care team",
    )

    def __iter__(self):
        if self.is_preview:
            return iter(self.__class__(is_preview=True) for c in range(3))
        return iter(
            self.__class__(context=SimpleNamespace(user=c["user_id"], role=c["role"]))
            for c in self.context
        )


class EncounterPatientFacilityTagContextBuilder(PatientTagContextBuilder):
    filterset_class = TagFilter
    __filterset_backends__ = [filters.DjangoFilterBackend]

    def get_context(self):
        return TagConfig.objects.filter(
            id__in=self.parent_context.patient.facility_tags.get(
                str(self.parent_context.facility.id), []
            )
        )


class EncounterTagContextBuilder(PatientTagContextBuilder):
    filterset_class = TagFilter
    __filterset_backends__ = [filters.DjangoFilterBackend]

    def get_context(self):
        return TagConfig.objects.filter(id__in=self.parent_context.tags or [])


class EncounterFacilityLocationContextBuilder(SingleObjectContextBuilder):
    def get_context(self):
        return getattr(self.parent_context, self.parent_attribute)

    name = Field(
        display="Location Name",
        preview_value="Ward A",
        description="Name of the facility location",
    )


class EncounterOrganizationsContextBuilder(QuerysetContextBuilder):
    def get_context(self):
        return EncounterOrganization.objects.filter(encounter_id=self.parent_context.id)

    organization = Field(
        display="Organization",
        preview_value="",
        mapping=lambda o: o.organization.name if o.organization else "",
        description="Organization associated with the encounter",
    )


HOSPITALIZATION_ADMIT_SOURCE_DISPLAY = {
    "hosp_trans": "Transferred from other hospital",
    "emd": "From accident/emergency department",
    "outp": "From outpatient department",
    "born": "Born in hospital",
    "gp": "General Practitioner referral",
    "mp": "Medical Practitioner/physician referral",
    "nursing": "From nursing home",
    "psych": "From psychiatric hospital",
    "rehab": "From rehabilitation facility",
    "other": "Other",
}

HOSPITALIZATION_DISCHARGE_DISPOSITION_DISPLAY = {
    "home": "Home",
    "alt_home": "Alternate Home",
    "other_hcf": "Other Health Care Facility",
    "hosp": "Hospital",
    "long": "Long-term Care Facility",
    "aadvice": "Against Medical Advice",
    "exp": "Expired",
    "psy": "Psychiatric Hospital",
    "rehab": "Rehabilitation Facility",
    "snf": "Skilled Nursing Facility",
    "oth": "Other",
}

HOSPITALIZATION_DIET_PREFERENCE_DISPLAY = {
    "vegetarian": "Vegetarian",
    "dairy_free": "Dairy Free",
    "nut_free": "Nut Free",
    "gluten_free": "Gluten Free",
    "vegan": "Vegan",
    "halal": "Halal",
    "kosher": "Kosher",
    "none": "None",
}


class EncounterHospitalizationContextBuilder(SingleObjectContextBuilder):
    def get_context(self):
        return self.parent_context.hospitalization or {}

    re_admission = Field(
        display="Re-admission",
        mapping=lambda h: h.get("re_admission"),
        preview_value="False",
        description="Whether the encounter is a re-admission",
    )
    admit_source = Field(
        display="Admit Source",
        mapping=lambda h: HOSPITALIZATION_ADMIT_SOURCE_DISPLAY.get(
            h.get("admit_source")
        )
        if h.get("admit_source")
        else "",
        preview_value="From accident/emergency department",
        description="Source of admission for the encounter",
    )
    discharge_disposition = Field(
        display="Discharge Disposition",
        mapping=lambda h: HOSPITALIZATION_DISCHARGE_DISPOSITION_DISPLAY.get(
            h.get("discharge_disposition")
        )
        if h.get("discharge_disposition")
        else "",
        preview_value="",
        description="Disposition of discharge for the encounter",
    )
    diet_preference = Field(
        display="Diet Preference",
        mapping=lambda h: HOSPITALIZATION_DIET_PREFERENCE_DISPLAY.get(
            h.get("diet_preference")
        )
        if h.get("diet_preference")
        else "",
        preview_value="Dairy Free",
        description="Diet preference for the encounter",
    )


class BaseEncounterReportContext(SingleObjectContextBuilder):
    status = Field(
        display="Encounter Status",
        mapping=lambda e: STATUS_DISPLAY.get(
            e.status, e.status.title() if e.status else ""
        ),
        preview_value="In Progress",
        description="Current status of the encounter",
    )

    encounter_class = Field(
        display="Encounter Class",
        mapping=lambda e: ENCOUNTER_CLASS_DISPLAY.get(
            e.encounter_class, e.encounter_class.title() if e.encounter_class else ""
        ),
        preview_value="Outpatient",
        description="Classification of the encounter",
    )
    care_team = Field(
        target_context=EncounterCareTeamContextBuilder,
        display="Care Team",
        preview_value="",
        description="Care team of the encounter",
    )

    current_location = Field(
        display="Current Location",
        target_context=EncounterFacilityLocationContextBuilder,
        preview_value="",
        description="Current location within the facility for the encounter",
    )

    start_time = Field(
        display="Encounter Start Time",
        mapping=lambda e: e.period.get("start") if e.period else None,
        preview_value="2026-01-12T10:01:45.088000Z",
        description="Start time of the encounter",
    )
    end_time = Field(
        display="Encounter End Time",
        mapping=lambda e: e.period.get("end")
        if e.period and e.period.get("end")
        else "Ongoing",
        preview_value="2026-01-12T10:01:45.088000Z",
        description="End time of the encounter",
    )
    organizations = Field(
        display="Associated Organizations",
        target_context=EncounterOrganizationsContextBuilder,
        preview_value="",
        description="Organizations associated with the encounter",
    )
    discharge_summary_advice = Field(
        display="Discharge Summary Advice",
        mapping="discharge_summary_advice",
        preview_value="Patient is advised to follow up in 2 weeks.",
        description="Discharge summary advice for the encounter",
    )
    patient_facility_tags = Field(
        target_context=EncounterPatientFacilityTagContextBuilder,
        display="Patient Facility Tags",
        preview_value="",
        description="Facility-specific tags associated with the patient for the encounter",
    )
    encounter_tags = Field(
        target_context=EncounterTagContextBuilder,
        display="Encounter Tags",
        preview_value="",
        description="Tags associated with the encounter",
    )
    priority = Field(
        display="Priority",
        mapping=lambda e: ENCOUNTER_PRIORITY_DISPLAY.get(
            e.priority, e.priority.title() if e.priority else ""
        ),
        preview_value="ASAP",
        description="Priority of the encounter",
    )
    hospitalization = Field(
        target_context=EncounterHospitalizationContextBuilder,
        display="Hospitalization",
        preview_value="",
        description="Hospitalization of the encounter",
    )
    external_identifier = Field(
        display="External Identifier",
        mapping="external_identifier",
        preview_value="1234567890",
        description="External identifier of the encounter",
    )


class MinimumEncounterReportContext(BaseEncounterReportContext):
    def get_context(self):
        return getattr(self.parent_context, self.parent_attribute)


class PatientFacilityIdentifiersContextBuilder(IdentifiersContextBuilder):
    def get_context(self):
        return self.parent_context.patient.facility_identifiers.get(
            str(self.parent_context.facility.id), []
        )


class EncounterReportContext(BaseEncounterReportContext):
    standalone_context = True
    __slug__ = "encounter_base"
    __associating_model__ = Encounter
    __display_name__ = "Encounter Report"
    __description__ = "Report context for encounter-based reports"
    context_key = "encounter"

    patient = Field(
        display="Patient Details",
        target_context=PatientMinimumContextBuilder,
        preview_value="",
        description="Details of the patient associated with the encounter",
    )

    facility = Field(
        display="Facility Details",
        target_context=FacilityContextBuilder,
        preview_value="",
        description="Details of the facility where the encounter took place",
    )

    diagnostic_reports = Field(
        display="Diagnostic Reports",
        preview_value="",
        description="Diagnostic reports associated with the encounter",
        target_context=DiagnosticReportContextBuilder,
    )
    symptoms = Field(
        target_context=SymptomsContextBuilder,
        display="Symptoms",
        preview_value="",
        description="Symptoms of the encounter",
    )
    allergy_intolerances = Field(
        target_context=AllergyIntoleranceContextBuilder,
        display="Allergy Intolerances",
        preview_value="",
        description="Allergy intolerances of the encounter",
    )
    diagnoses = Field(
        target_context=DiagnosisContextBuilder,
        display="Diagnoses",
        preview_value="",
        description="Diagnoses of the encounter",
    )

    questionnaire_responses = Field(
        target_context=QuestionnaireContextBuilder,
        display="Questionnaire Responses",
        preview_value="",
        description="Questionnaire responses of the encounter",
    )

    medication_prescriptions = Field(
        display="Medication Prescriptions",
        target_context=MedicationPrescriptionContextBuilder,
        preview_value="",
        description="Medication prescriptions of the encounter",
    )

    service_requests = Field(
        display="Service Requests",
        target_context=ServiceRequestBaseContextBuilder,
        preview_value="",
        description="Service requests associated with the encounter",
    )

    facility_identifiers = Field(
        display="Facility Identifiers",
        target_context=PatientFacilityIdentifiersContextBuilder,
        preview_value="",
        description="Facility identifiers associated with the encounter",
    )


DataPointRegistry.register(EncounterReportContext)
