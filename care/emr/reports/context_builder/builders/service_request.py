from care.emr.models import Encounter
from care.emr.models.service_request import ServiceRequest
from care.emr.reports.context_builder.base import Field, QuerysetContextBuilder
from care.emr.reports.context_builder.registry import context_builder_registry
from care.emr.reports.context_builder.utils import format_datetime

STATUS_DISPLAY = {
    "draft": "Draft",
    "active": "Active",
    "on_hold": "On Hold",
    "revoked": "Revoked",
    "completed": "Completed",
    "entered_in_error": "Entered in Error",
    "unknown": "Unknown",
}

INTENT_DISPLAY = {
    "proposal": "Proposal",
    "plan": "Plan",
    "directive": "Directive",
    "order": "Order",
    "original_order": "Original Order",
    "reflex_order": "Reflex Order",
    "filler_order": "Filler Order",
    "instance_order": "Instance Order",
    "option": "Option",
}

PRIORITY_DISPLAY = {
    "routine": "Routine",
    "urgent": "Urgent",
    "asap": "ASAP",
    "stat": "STAT",
}


class ServiceRequestContextBuilder(QuerysetContextBuilder):
    model = ServiceRequest
    depends_on = ["encounter_id"]

    base_filters = {}
    allowed_filters = [
        ServiceRequest.status,
        ServiceRequest.intent,
        ServiceRequest.priority,
        ServiceRequest.category,
        ServiceRequest.occurance,
    ]

    fields = [
        Field(
            key="title",
            display="Service Title",
            mapping="title",
            preview_value="CT Scan - Chest",
            description="Title/name of the service requested",
        ),
        Field(
            key="category",
            display="Category",
            mapping=lambda s: s.category.replace("_", " ").title()
            if s.category
            else "",
            preview_value="Diagnostic Procedure",
            description="Category of the service",
        ),
        Field(
            key="status",
            display="Status",
            mapping=lambda s: STATUS_DISPLAY.get(
                s.status, s.status.replace("_", " ").title() if s.status else ""
            ),
            preview_value="Active",
            description="Current status of the service request",
        ),
        Field(
            key="intent",
            display="Intent",
            mapping=lambda s: INTENT_DISPLAY.get(
                s.intent, s.intent.title() if s.intent else ""
            ),
            preview_value="Order",
            description="Intent of the service request",
        ),
        Field(
            key="priority",
            display="Priority",
            mapping=lambda s: PRIORITY_DISPLAY.get(
                s.priority, s.priority.title() if s.priority else ""
            ),
            preview_value="Routine",
            description="Priority of the service request",
        ),
        Field(
            key="occurrence_date",
            display="Occurrence Date",
            mapping=lambda s: format_datetime(s.occurance) if s.occurance else "",
            preview_value="20/01/2024 10:00 AM",
            description="When the service is to be performed",
        ),
        Field(
            key="note",
            display="Notes",
            mapping="note",
            preview_value="Patient requires fasting for 12 hours before procedure",
            description="Additional notes and instructions",
        ),
        Field(
            key="patient_instruction",
            display="Patient Instructions",
            mapping="patient_instruction",
            preview_value="Come on empty stomach, bring previous reports",
            description="Instructions for the patient",
        ),
        Field(
            key="do_not_perform",
            display="Do Not Perform",
            mapping=lambda s: "Yes" if s.do_not_perform else "No",
            preview_value="No",
            description="Whether the service should not be performed",
        ),
        Field(
            key="code",
            display="Service Code",
            mapping=lambda s: s.code.get("display", "")
            if s.code and isinstance(s.code, dict)
            else "",
            preview_value="CT123",
            description="Coded value for the service",
        ),
        Field(
            key="body_site",
            display="Body Site",
            mapping=lambda s: s.body_site.get("display", "")
            if s.body_site and isinstance(s.body_site, dict)
            else "",
            preview_value="Chest",
            description="Target body site for the service",
        ),
        Field(
            key="healthcare_service_name",
            display="Healthcare Service",
            mapping=lambda s: s.healthcare_service.name if s.healthcare_service else "",
            preview_value="Radiology Department",
            description="Healthcare service providing the service",
        ),
        Field(
            key="requester_name",
            display="Requester",
            mapping=lambda s: s.requester.full_name if s.requester else "",
            preview_value="Dr. Rajesh Kumar",
            description="Person who requested the service",
        ),
        Field(
            key="created_date",
            display="Created Date",
            mapping=lambda s: format_datetime(s.created_date) if s.created_date else "",
            preview_value="15/01/2024 02:30 PM",
            description="When the request was created",
        ),
    ]

    @classmethod
    def get_queryset(cls, ctx: dict):
        encounter_id = ctx.get("encounter_id")
        encounter = Encounter.objects.get(external_id=encounter_id)

        queryset = cls.model.objects.filter(encounter=encounter).select_related(
            "healthcare_service", "requester"
        )

        if cls.base_filters:
            queryset = queryset.filter(**cls.base_filters)

        return queryset

    @classmethod
    def get_display_name(cls):
        return "Service Requests"

    @classmethod
    def get_description(cls):
        return "Requested healthcare services and procedures"


context_builder_registry.register("service_requests", ServiceRequestContextBuilder)
