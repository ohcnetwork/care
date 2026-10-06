"""People, places and visits: who the caller is, facilities, patients, encounters."""

from care_mcp.tools.base import UUID, ToolError, page, tool

ENCOUNTER_STATUSES = [
    "planned",
    "in_progress",
    "on_hold",
    "discharged",
    "completed",
    "cancelled",
    "discontinued",
    "entered_in_error",
    "unknown",
]
ENCOUNTER_CLASSES = ["imp", "amb", "obsenc", "emer", "vr", "hh"]


@tool(
    "get_current_user",
    "Current user",
    """
    Who the MCP caller is in Care: name, username, roles, permissions, and the
    facilities and organizations they belong to. Call this first to find the
    facility IDs to pass to other tools.
    """,
)
def get_current_user(ctx, args):
    return ctx.get("users/getcurrentuser/")


@tool(
    "search_users",
    "Search users",
    "Search Care staff users by name or username.",
    {"search": {"type": "string", "description": "Name or username to match."}},
    paginated=True,
)
def search_users(ctx, args):
    return ctx.get("users/", {"search_text": args.get("search"), **page(args)})


@tool(
    "list_facilities",
    "List facilities",
    "List the facilities the current user can see, optionally filtered by name.",
    {
        "name": {"type": "string", "description": "Part of the facility name."},
        "organization_id": {
            **UUID,
            "description": "Only facilities inside this geographic organization.",
        },
    },
    paginated=True,
)
def list_facilities(ctx, args):
    return ctx.get(
        "facility/",
        {
            "name": args.get("name"),
            "organization": args.get("organization_id"),
            **page(args),
        },
    )


@tool(
    "get_facility",
    "Get facility",
    "Details of one facility: address, type, features and contact information.",
    {"facility_id": UUID},
    ["facility_id"],
)
def get_facility(ctx, args):
    return ctx.get(f"facility/{args['facility_id']}/")


@tool(
    "search_patients",
    "Search patients",
    """
    Search patients by name or phone number across the organizations the user
    has patient-list access to. Facility staff usually find patients through
    list_encounters with a facility_id instead, because this list only includes
    patients in the user's own geographic organizations.
    """,
    {
        "name": {"type": "string", "description": "Part of the patient's name."},
        "phone_number": {
            "type": "string",
            "description": "Exact phone number in E.164 form, e.g. +919876543210.",
        },
        "organization_id": {
            **UUID,
            "description": "Only patients in this geographic organization.",
        },
    },
    paginated=True,
)
def search_patients(ctx, args):
    return ctx.get(
        "patient/",
        {
            "name": args.get("name"),
            "phone_number": args.get("phone_number"),
            "organization": args.get("organization_id"),
            "ordering": "-modified_date",
            **page(args),
        },
    )


@tool(
    "get_patient",
    "Get patient",
    "Demographics, contact details, identifiers and tags of one patient.",
    {"patient_id": UUID},
    ["patient_id"],
)
def get_patient(ctx, args):
    return ctx.get(f"patient/{args['patient_id']}/")


@tool(
    "list_encounters",
    "List encounters",
    """
    List encounters (visits, admissions, consultations) at a facility or for a
    patient. One of facility_id or patient_id is required. Use active_only to get
    patients currently under care, e.g. "who is admitted right now".
    """,
    {
        "facility_id": UUID,
        "patient_id": UUID,
        "active_only": {
            "type": "boolean",
            "description": (
                "Only encounters that are not completed, cancelled, discontinued "
                "or entered in error."
            ),
        },
        "status": {
            "type": "array",
            "items": {"enum": ENCOUNTER_STATUSES},
            "description": "Only encounters with one of these statuses.",
        },
        "encounter_class": {
            "enum": ENCOUNTER_CLASSES,
            "description": (
                "imp = inpatient, amb = outpatient, obsenc = observation, "
                "emer = emergency, vr = virtual, hh = home health."
            ),
        },
        "patient_name": {"type": "string", "description": "Part of the name."},
        "patient_phone_number": {"type": "string"},
        "location_id": {
            **UUID,
            "description": "Only encounters currently at this location (ward, bed).",
        },
        "created_after": {"type": "string", "format": "date-time"},
        "created_before": {"type": "string", "format": "date-time"},
    },
    paginated=True,
)
def list_encounters(ctx, args):
    if not args.get("facility_id") and not args.get("patient_id"):
        msg = "Pass facility_id or patient_id."
        raise ToolError(msg)
    query = {
        "facility": args.get("facility_id"),
        "patient": args.get("patient_id"),
        "status": args.get("status"),
        "encounter_class": args.get("encounter_class"),
        "name": args.get("patient_name"),
        "phone_number": args.get("patient_phone_number"),
        "location": args.get("location_id"),
        "created_date_after": args.get("created_after"),
        "created_date_before": args.get("created_before"),
        "ordering": "-created_date",
        **page(args),
    }
    if args.get("active_only"):
        # Care's `live=false` excludes the completed-like statuses.
        query["live"] = False
    return ctx.get("encounter/", query)


@tool(
    "get_encounter",
    "Get encounter",
    """
    Full details of one encounter: patient, facility, status history, class,
    priority, current location, care team, hospitalization and discharge details.
    """,
    {"encounter_id": UUID},
    ["encounter_id"],
)
def get_encounter(ctx, args):
    return ctx.get(f"encounter/{args['encounter_id']}/")
