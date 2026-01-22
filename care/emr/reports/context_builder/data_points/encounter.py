from types import SimpleNamespace

from care.emr.models.encounter import Encounter
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
    PatientMinimumContextBuilder,
)
from care.emr.reports.context_builder.data_points.questionnaire import (
    QuestionnaireContextBuilder,
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


class EncounterFacilityLocationContextBuilder(SingleObjectContextBuilder):
    def get_context(self):
        return getattr(self.parent_context, self.parent_attribute)

    name = Field(
        display="Location Name",
        preview_value="Ward A",
        description="Name of the facility location",
    )


class EncounterReportContextBase(SingleObjectContextBuilder):
    standalone_context = True
    __slug__ = "encounter_base"
    __associating_model__ = Encounter
    __display_name__ = "Encounter Report"
    __description__ = "Report context for encounter-based reports"
    context_key = "encounter"

    status = Field(
        display="Encounter Status",
        mapping=lambda e: STATUS_DISPLAY.get(
            e.status, e.status.title() if e.status else ""
        ),
        preview_value="In Progress",
        description="Current status of the encounter",
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
    care_team = Field(
        target_context=EncounterCareTeamContextBuilder,
        display="Care Team",
        preview_value="",
        description="Care team of the encounter",
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
    patient = Field(
        display="Patient Details",
        target_context=PatientMinimumContextBuilder,
        preview_value="",
        description="Details of the patient associated with the encounter",
    )

    diagnostic_reports = Field(
        display="Diagnostic Reports",
        preview_value="",
        description="Diagnostic reports associated with the encounter",
        target_context=DiagnosticReportContextBuilder,
    )

    facility = Field(
        display="Facility Details",
        target_context=FacilityContextBuilder,
        preview_value="",
        description="Details of the facility where the encounter took place",
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


DataPointRegistry.register(EncounterReportContextBase)
