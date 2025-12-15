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
from care.emr.reports.context_builder.data_points.medication import (
    MedicationPrescriptionContextBuilder,
)
from care.emr.reports.context_builder.data_points.questionnaire import (
    QuestionnaireContextBuilder,
)
from care.emr.reports.context_builder.data_points.service_request import (
    ServiceRequestDataPointBuilder,
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
        preview_value={"display": "Test Role"},
        description="Role of the user in the encounter care team",
    )

    def __iter__(self):
        if self.is_preview:
            return iter(self.__class__(is_preview=True) for c in range(3))
        return iter(
            self.__class__(context=SimpleNamespace(user=c["user_id"], role=c["role"]))
            for c in self.context
        )


class EncounterPatientContextBuilder(SingleObjectContextBuilder):
    def get_context(self):
        return self.parent_context.patient

    name = Field(
        display="Patient Name",
        preview_value="John Doe",
        description="Full name of the patient",
    )
    age = Field(
        display="Patient Age",
        mapping=lambda p: p.get_age(),
        preview_value="30 Y",
        description="Age of the patient",
    )

    gender = Field(
        display="Patient Gender",
        mapping=lambda p: p.gender,
        preview_value="Male",
        description="Gender of the patient",
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
        target_context=EncounterPatientContextBuilder,
        preview_value="",
        description="Details of the patient associated with the encounter",
    )

    service_requests = Field(
        display="Service Requests",
        target_context=ServiceRequestDataPointBuilder,
        preview_value="",
        description="Service requests associated with the encounter",
    )


DataPointRegistry.register(EncounterReportContextBase)
