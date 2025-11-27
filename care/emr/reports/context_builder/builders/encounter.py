from care.emr.models.encounter import Encounter
from care.emr.reports.context_builder.base import Field, SingleObjectContextBuilder
from care.emr.reports.context_builder.registry import context_builder_registry
from care.emr.reports.context_builder.utils import format_datetime
from care.users.models import User

STATUS_DISPLAY = {
    "planned": "Planned",
    "in_progress": "In Progress",
    "completed": "Completed",
    "cancelled": "Cancelled",
    "entered_in_error": "Entered in Error",
}

ENCOUNTER_CLASS_DISPLAY = {
    "imp": "Inpatient",
    "amb": "Ambulatory",
    "obsenc": "Observation",
    "emer": "Emergency",
    "vr": "Virtual",
    "hh": "Home Health",
}


class EncounterContextBuilder(SingleObjectContextBuilder):
    model = Encounter
    depends_on = ["encounter_id"]

    fields = [
        Field(
            key="status",
            display="Encounter Status",
            mapping=lambda e: STATUS_DISPLAY.get(
                e.status, e.status.title() if e.status else ""
            ),
            preview_value="In Progress",
            description="Current status of the encounter",
        ),
        Field(
            key="encounter_class",
            display="Encounter Type",
            mapping=lambda e: ENCOUNTER_CLASS_DISPLAY.get(
                e.encounter_class,
                e.encounter_class.title() if e.encounter_class else "",
            ),
            preview_value="Inpatient",
            description="Type of encounter (Ambulatory/Inpatient/Emergency/Virtual/etc.)",
        ),
        Field(
            key="admission_date",
            display="Admission Date & Time",
            mapping=lambda e: format_datetime(e.period.get("start"))
            if e.period and e.period.get("start")
            else "",
            preview_value="15/01/2024 10:30 AM",
            description="Date and time of admission",
        ),
        Field(
            key="discharge_date",
            display="Discharge Date & Time",
            mapping=lambda e: format_datetime(e.period.get("end"))
            if e.period and e.period.get("end")
            else "",
            preview_value="20/01/2024 02:00 PM",
            description="Date and time of discharge",
        ),
        Field(
            key="facility_name",
            display="Facility Name",
            mapping=lambda e: e.facility.name if e.facility else "",
            preview_value="City General Hospital",
            description="Name of the healthcare facility",
        ),
        Field(
            key="facility_address",
            display="Facility Address",
            mapping=lambda e: e.facility.address if e.facility else "",
            preview_value="789, Hospital Road, Bangalore - 560001",
            description="Address of the healthcare facility",
        ),
        Field(
            key="priority",
            display="Priority",
            mapping=lambda e: e.priority.title() if e.priority else "",
            preview_value="Routine",
            description="Priority level of the encounter",
        ),
        Field(
            key="external_identifier",
            display="Visit/Admission Number",
            mapping="external_identifier",
            preview_value="ADM/2024/00123",
            description="External identifier for the encounter",
        ),
        Field(
            key="discharge_summary_advice",
            display="Discharge Summary Advice",
            mapping="discharge_summary_advice",
            preview_value="Patient advised to continue medications and follow up after 1 week.",
            description="Discharge advice and instructions",
        ),
        Field(
            key="care_team",
            display="Care Team",
            field_type="list[CareTeamMember]",
            mapping=lambda e: EncounterContextBuilder._format_care_team(e),
            preview_value=[
                {"name": "Dr. Rajesh Kumar", "role": "Primary Physician"},
                {"name": "Nurse Sarah", "role": "Primary Nurse"},
            ],
            description="Healthcare professionals involved in patient care",
        ),
    ]

    @staticmethod
    def _format_care_team(encounter):
        care_team = encounter.care_team

        if not care_team:
            return []

        if isinstance(care_team, dict):
            return []

        if not isinstance(care_team, list):
            return []

        user_ids = [
            member.get("user_id")
            for member in care_team
            if isinstance(member, dict) and member.get("user_id")
        ]

        if not user_ids:
            return []

        role_map = {
            member.get("user_id"): member.get("role", {}).get("display", "Unknown")
            for member in care_team
            if isinstance(member, dict) and member.get("user_id") and member.get("role")
        }

        users = User.objects.filter(id__in=user_ids)
        return [
            {
                "name": user.full_name or "Unknown",
                "role": role_map.get(user.id, "Unknown"),
            }
            for user in users
        ]

    @classmethod
    def get_object(cls, ctx: dict):
        encounter_id = ctx.get("encounter_id")
        return Encounter.objects.get(external_id=encounter_id)

    @classmethod
    def get_display_name(cls):
        return "Encounter Details"

    @classmethod
    def get_description(cls):
        return "Encounter details"


context_builder_registry.register("encounter", EncounterContextBuilder)
