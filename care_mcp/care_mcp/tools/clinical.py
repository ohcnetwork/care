"""A patient's clinical record: conditions, allergies, medications, observations…

Care checks clinical access per patient. A user with access to the patient (for
example through their organization) can read everything; a user who only has
access through an encounter must pass that encounter_id, which also limits the
results to that encounter.
"""

from care_mcp.tools.base import UUID, ToolError, page, tool

PATIENT_AND_ENCOUNTER = {
    "patient_id": UUID,
    "encounter_id": {
        **UUID,
        "description": (
            "Only records from this encounter. Required when the user's access to "
            "the patient comes from the encounter."
        ),
    },
}

CLINICAL_STATUSES = [
    "active",
    "recurrence",
    "relapse",
    "inactive",
    "remission",
    "resolved",
    "unknown",
]
VERIFICATION_STATUSES = [
    "unconfirmed",
    "provisional",
    "differential",
    "confirmed",
    "refuted",
    "entered_in_error",
]


def _patient_path(args, resource):
    return f"patient/{args['patient_id']}/{resource}/"


@tool(
    "list_conditions",
    "List diagnoses and symptoms",
    """
    A patient's diagnoses (encounter diagnoses and chronic conditions) or symptoms,
    with clinical and verification status, severity and onset.
    """,
    {
        **PATIENT_AND_ENCOUNTER,
        "kind": {
            "enum": ["diagnosis", "symptom"],
            "default": "diagnosis",
            "description": "diagnosis or symptom.",
        },
        "clinical_status": {"type": "array", "items": {"enum": CLINICAL_STATUSES}},
        "verification_status": {
            "type": "array",
            "items": {"enum": VERIFICATION_STATUSES},
        },
        "include_entered_in_error": {"type": "boolean", "default": False},
    },
    ["patient_id"],
    paginated=True,
)
def list_conditions(ctx, args):
    kind = args.get("kind", "diagnosis")
    query = {
        "encounter": args.get("encounter_id"),
        "clinical_status": args.get("clinical_status"),
        "verification_status": args.get("verification_status"),
        "ordering": "-created_date",
        **page(args),
    }
    if kind == "diagnosis":
        # The diagnosis endpoint is not limited to diagnoses by itself.
        query["category"] = ["encounter_diagnosis", "chronic_condition"]
    if not args.get("include_entered_in_error"):
        query["exclude_verification_status"] = "entered_in_error"
    return ctx.get(_patient_path(args, kind), query)


@tool(
    "list_allergies",
    "List allergies",
    "A patient's allergies and intolerances, with criticality and status.",
    {
        **PATIENT_AND_ENCOUNTER,
        "clinical_status": {
            "type": "array",
            "items": {"enum": ["active", "inactive", "resolved"]},
        },
    },
    ["patient_id"],
    paginated=True,
)
def list_allergies(ctx, args):
    return ctx.get(
        _patient_path(args, "allergy_intolerance"),
        {
            "encounter": args.get("encounter_id"),
            "clinical_status": args.get("clinical_status"),
            "exclude_verification_status": "entered_in_error",
            **page(args),
        },
    )


MEDICATION_KINDS = {
    "request": "medication/request",
    "statement": "medication/statement",
    "administration": "medication/administration",
}


@tool(
    "list_medications",
    "List medications",
    """
    A patient's medications. kind=request gives prescriptions ordered in Care,
    kind=statement gives medications the patient reports taking, and
    kind=administration gives doses actually given (the medication chart).
    """,
    {
        **PATIENT_AND_ENCOUNTER,
        "kind": {
            "enum": list(MEDICATION_KINDS),
            "default": "request",
        },
        "status": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Status filter. request: active, on_hold, ended, stopped, completed, "
                "cancelled, draft. statement: active, on_hold, completed, stopped, "
                "not_taken, intended. administration: completed, not_done, "
                "in_progress, on_hold, stopped, cancelled."
            ),
        },
        "medication_request_id": {
            **UUID,
            "description": "For kind=administration: doses given for this request.",
        },
    },
    ["patient_id"],
    paginated=True,
)
def list_medications(ctx, args):
    kind = args.get("kind", "request")
    return ctx.get(
        _patient_path(args, MEDICATION_KINDS[kind]),
        {
            "encounter": args.get("encounter_id"),
            "status": args.get("status"),
            "request": args.get("medication_request_id"),
            "ordering": "-created_date",
            **page(args),
        },
    )


@tool(
    "list_observations",
    "List observations",
    """
    A patient's recorded observations (vitals, lab values, assessment answers),
    newest first. Filter by codes to get one measurement, e.g. a LOINC code.
    """,
    {
        **PATIENT_AND_ENCOUNTER,
        "codes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Only observations with one of these codes.",
        },
        "status": {
            "type": "array",
            "items": {"enum": ["final", "amended", "entered_in_error"]},
        },
    },
    ["patient_id"],
    paginated=True,
)
def list_observations(ctx, args):
    return ctx.get(
        _patient_path(args, "observation"),
        {
            "encounter": args.get("encounter_id"),
            "codes": args.get("codes"),
            "status": args.get("status") or ["final", "amended"],
            "ignore_group": True,
            **page(args),
        },
    )


@tool(
    "observation_trends",
    "Observation trends",
    """
    Recent values of specific observations for a patient, grouped by code, for
    spotting trends (e.g. blood pressure over the last readings). Get the code
    and system from list_observations first.
    """,
    {
        "patient_id": UUID,
        "codes": {
            "type": "array",
            "minItems": 1,
            "maxItems": 20,
            "items": {
                "type": "object",
                "properties": {
                    "system": {"type": "string"},
                    "code": {"type": "string"},
                },
                "required": ["system", "code"],
            },
        },
        "per_code": {
            "type": "integer",
            "minimum": 1,
            "maximum": 30,
            "default": 10,
            "description": "How many recent values per code.",
        },
    },
    ["patient_id", "codes"],
)
def observation_trends(ctx, args):
    return ctx.post_read(
        _patient_path(args, "observation/analyse"),
        {"codes": args["codes"], "page_size": args.get("per_code", 10)},
    )


@tool(
    "list_questionnaire_responses",
    "List form responses",
    """
    Forms and questionnaires filled for a patient (assessments, notes captured
    as structured forms), with their answers.
    """,
    {
        **PATIENT_AND_ENCOUNTER,
        "questionnaire_slug": {"type": "string"},
    },
    ["patient_id"],
    paginated=True,
)
def list_questionnaire_responses(ctx, args):
    return ctx.get(
        _patient_path(args, "questionnaire_response"),
        {
            "encounter": args.get("encounter_id"),
            "questionnaire_slug": args.get("questionnaire_slug"),
            "status": "completed",
            **page(args),
        },
    )


@tool(
    "list_diagnostic_reports",
    "List diagnostic reports",
    "A patient's lab and imaging reports with their status and conclusions.",
    {
        **PATIENT_AND_ENCOUNTER,
        "status": {"enum": ["registered", "partial", "preliminary", "final"]},
    },
    ["patient_id"],
    paginated=True,
)
def list_diagnostic_reports(ctx, args):
    return ctx.get(
        _patient_path(args, "diagnostic_report"),
        {
            "encounter": args.get("encounter_id"),
            "status": args.get("status"),
            "ordering": "-created_date",
            **page(args),
        },
    )


@tool(
    "list_service_requests",
    "List service requests",
    """
    Orders (lab tests, imaging, procedures) at a facility, for an encounter or a
    location. One of encounter_id or location_id is required.
    """,
    {
        "facility_id": UUID,
        "encounter_id": UUID,
        "location_id": UUID,
        "status": {
            "enum": [
                "draft",
                "active",
                "on_hold",
                "entered_in_error",
                "ended",
                "completed",
                "revoked",
            ]
        },
    },
    ["facility_id"],
    paginated=True,
)
def list_service_requests(ctx, args):
    if not args.get("encounter_id") and not args.get("location_id"):
        msg = "Pass encounter_id or location_id."
        raise ToolError(msg)
    return ctx.get(
        f"facility/{args['facility_id']}/service_request/",
        {
            "encounter": args.get("encounter_id"),
            "location": args.get("location_id"),
            "status": args.get("status"),
            "ordering": "-created_date",
            **page(args),
        },
    )


@tool(
    "get_notes",
    "Get clinical notes",
    """
    Discussion notes on a patient, grouped by thread, with the most recent
    messages of each thread.
    """,
    {
        **PATIENT_AND_ENCOUNTER,
        "messages_per_thread": {
            "type": "integer",
            "minimum": 1,
            "maximum": 50,
            "default": 10,
        },
    },
    ["patient_id"],
    paginated=True,
)
def get_notes(ctx, args):
    encounter = args.get("encounter_id")
    threads = ctx.get(
        _patient_path(args, "thread"), {"encounter": encounter, **page(args)}
    )
    for thread in threads.get("results", []):
        messages = ctx.get(
            f"patient/{args['patient_id']}/thread/{thread['id']}/note/",
            {"encounter": encounter, "limit": args.get("messages_per_thread", 10)},
        )
        thread["messages"] = messages.get("results", [])
        thread["message_count"] = messages.get("count")
    return threads
