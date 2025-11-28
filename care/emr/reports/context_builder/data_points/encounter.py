from types import SimpleNamespace

from care.emr.reports.context_builder.data_point_registry import DataPointRegistry
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
    SingleObjectContextBuilder,
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
    def get_context(self) -> dict:
        return self.parent_context.care_team

    user = Field(
        key="user",
        display="User",
        target_context=SingleUserIdContextBuilder,
        preview_value="",
        description="User who is part of the encounter care team",
    )
    role = Field(
        key="role",
        display="Role",
        preview_value={
            "code": "12334",
            "system": "http://careterms.info/terms",
            "display": "Test Role",
        },
        description="Role of the user in the encounter care team",
    )

    def __iter__(self):
        if self.is_preview:
            return iter(self.__class__(is_preview=True) for c in range(3))
        return iter(
            self.__class__(context=SimpleNamespace(user=c["user_id"], role=c["role"]))
            for c in self.context
        )


class EncounterReportContextBase(SingleObjectContextBuilder):
    standalone_context = True
    __slug__ = "encounter_base"
    context_key = "encounter"

    status = Field(
        key="status",
        display="Encounter Status",
        mapping=lambda e: STATUS_DISPLAY.get(
            e.status, e.status.title() if e.status else ""
        ),
        preview_value="In Progress",
        description="Current status of the encounter",
    )
    symptoms = Field(
        key="symptoms",
        target_context=SymptomsContextBuilder,
        display="Symptoms",
        preview_value="",
        description="Symptoms of the encounter",
    )
    care_team = Field(
        key="care_team",
        target_context=EncounterCareTeamContextBuilder,
        display="Care Team",
        preview_value="",
        description="Care team of the encounter",
    )
    questionnaire_responses = Field(
        key="questionnaire_responses",
        target_context=QuestionnaireContextBuilder,
        display="Questionnaire Responses",
        preview_value="",
        description="Questionnaire responses of the encounter",
    )


DataPointRegistry.register(EncounterReportContextBase)
