"""Composite tools that save the model a dozen round trips."""

from care_mcp.tools.base import UUID, ToolError, tool


def _section(fn):
    """Run one part of a summary; a part the user can't see becomes an error note."""
    try:
        data = fn()
    except ToolError as e:
        return {"error": e.message, "details": e.data}
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


@tool(
    "get_patient_summary",
    "Patient summary",
    """
    One-call clinical snapshot of a patient: demographics, the encounter (or the
    patient's open encounters), active diagnoses and symptoms, allergies, active
    medication requests and the latest observations. Use this before answering
    broad questions about a patient. Pass encounter_id when the user's access to
    the patient comes through an encounter.
    """,
    {
        "patient_id": UUID,
        "encounter_id": UUID,
        "observation_limit": {
            "type": "integer",
            "minimum": 0,
            "maximum": 50,
            "default": 15,
        },
    },
    ["patient_id"],
)
def get_patient_summary(ctx, args):
    patient_id = args["patient_id"]
    encounter_id = args.get("encounter_id")
    base = f"patient/{patient_id}"
    scope = {"encounter": encounter_id}
    active = ["active", "recurrence", "relapse"]

    patient = ctx.get(f"{base}/")
    # The caller's own permission list on the patient is noise in a summary.
    patient.pop("permissions", None)
    summary = {"patient": patient}
    if encounter_id:
        summary["encounter"] = _section(lambda: ctx.get(f"encounter/{encounter_id}/"))
    else:
        summary["open_encounters"] = _section(
            lambda: ctx.get(
                "encounter/", {"patient": patient_id, "live": False, "limit": 5}
            )
        )
    summary["diagnoses"] = _section(
        lambda: ctx.get(
            f"{base}/diagnosis/",
            {
                **scope,
                "category": ["encounter_diagnosis", "chronic_condition"],
                "clinical_status": active,
                "exclude_verification_status": ["entered_in_error", "refuted"],
                "limit": 50,
            },
        )
    )
    summary["symptoms"] = _section(
        lambda: ctx.get(
            f"{base}/symptom/",
            {
                **scope,
                "clinical_status": active,
                "exclude_verification_status": ["entered_in_error", "refuted"],
                "limit": 50,
            },
        )
    )
    summary["allergies"] = _section(
        lambda: ctx.get(
            f"{base}/allergy_intolerance/",
            {
                **scope,
                "clinical_status": "active",
                "exclude_verification_status": ["entered_in_error", "refuted"],
                "limit": 50,
            },
        )
    )
    summary["active_medications"] = _section(
        lambda: ctx.get(
            f"{base}/medication/request/",
            {**scope, "status": ["active", "on_hold"], "limit": 50},
        )
    )
    observation_limit = args.get("observation_limit", 15)
    if observation_limit:
        summary["recent_observations"] = _section(
            lambda: ctx.get(
                f"{base}/observation/",
                {
                    **scope,
                    "status": ["final", "amended"],
                    "ignore_group": True,
                    "limit": observation_limit,
                },
            )
        )
    return summary
