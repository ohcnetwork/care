"""MCP over JSON-RPC 2.0: lifecycle, tools and prompts.

The server is stateless: every request carries its own credentials and nothing
is kept between requests, so it runs behind any number of Care workers and
needs no session store. That is allowed by the Streamable HTTP transport, which
makes session IDs optional.
"""

import json
import logging
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from care_mcp.settings import plugin_settings
from care_mcp.tools import REGISTRY, ToolContext, ToolError

logger = logging.getLogger(__name__)

# Newest first. A client asking for one of these gets it back; anything else
# gets the newest, and the client decides whether it can continue.
SUPPORTED_PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26")
SERVER_VERSION = "0.1.0"

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

INSTRUCTIONS = """\
You are connected to CARE, an open-source electronic medical record and hospital \
management system, as a specific Care user. Every tool runs with that user's \
permissions: you only see what they could see in Care's web app.

Typical flow: call get_current_user to learn the user's facilities, find patients \
with list_encounters (facility_id, active_only=true) or search_patients, then use \
get_patient_summary for an overview and the list_* tools for detail. IDs are UUIDs \
taken from earlier results. If a clinical tool returns 403, pass the encounter_id \
through which the user has access. For anything without a dedicated tool, use \
list_api_endpoints and care_api_get.

This is patient data. Quote values as recorded, say when data is missing rather \
than guessing, and do not repeat identifiers or contact details unless asked.\
"""

PROMPTS = {
    "patient_summary": {
        "title": "Summarise a patient",
        "description": "Clinical summary of a patient, optionally for one encounter.",
        "arguments": [
            {"name": "patient_id", "description": "Patient UUID", "required": True},
            {
                "name": "encounter_id",
                "description": "Encounter UUID (optional)",
                "required": False,
            },
        ],
        "template": (
            "Use get_patient_summary for patient {patient_id}{encounter_clause}. "
            "Write a concise clinical summary for a clinician: who the patient is, "
            "why they are under care, active problems, allergies, current "
            "medications, and the latest vitals and results with any abnormal "
            "values called out. Say explicitly what is not recorded."
        ),
    },
    "shift_handover": {
        "title": "Shift handover for a facility",
        "description": "Handover notes for the patients currently admitted at a facility.",
        "arguments": [
            {"name": "facility_id", "description": "Facility UUID", "required": True},
        ],
        "template": (
            "List the active inpatient encounters at facility {facility_id} with "
            "list_encounters (active_only=true, encounter_class=imp). For each "
            "patient, call get_patient_summary with the encounter_id and write a "
            "short handover entry: location, working diagnosis, current "
            "medications, latest vitals, and anything pending or concerning."
        ),
    },
}


class JSONRPCError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def _negotiate_version(requested) -> str:
    if requested in SUPPORTED_PROTOCOL_VERSIONS:
        return requested
    return SUPPORTED_PROTOCOL_VERSIONS[0]


def _visible_tools(ctx: ToolContext):
    return [t for t in REGISTRY.values() if ctx.allow_writes or not t.requires_writes]


def _truncate(text: str) -> str:
    limit = plugin_settings.CARE_MCP_MAX_RESPONSE_CHARS
    if limit and len(text) > limit:
        omitted = len(text) - limit
        return (
            text[:limit] + f"\n…[truncated {omitted} characters. Narrow the request "
            "with filters, or page with a smaller limit and an offset.]"
        )
    return text


def _text_result(data: Any, *, is_error: bool = False) -> dict:
    text = data if isinstance(data, str) else json.dumps(data, separators=(",", ":"))
    return {"content": [{"type": "text", "text": _truncate(text)}], "isError": is_error}


def handle_initialize(ctx, params):
    return {
        "protocolVersion": _negotiate_version(params.get("protocolVersion")),
        "capabilities": {
            "tools": {"listChanged": False},
            "prompts": {"listChanged": False},
        },
        "serverInfo": {
            "name": "care",
            "title": "CARE EMR",
            "version": SERVER_VERSION,
        },
        "instructions": INSTRUCTIONS,
    }


def handle_tools_list(ctx, params):
    return {"tools": [t.definition() for t in _visible_tools(ctx)]}


def handle_tools_call(ctx, params):
    name = params.get("name")
    arguments = params.get("arguments") or {}
    tool = next((t for t in _visible_tools(ctx) if t.name == name), None)
    if tool is None:
        raise JSONRPCError(INVALID_PARAMS, f"Unknown tool: {name}")
    if not isinstance(arguments, dict):
        raise JSONRPCError(INVALID_PARAMS, "Tool arguments must be an object.")

    # Bad arguments are reported as a tool error, so the model can correct itself.
    validator = Draft202012Validator(tool.input_schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(arguments), key=lambda e: list(e.path))
    if errors:
        details = [
            f"{'.'.join(str(p) for p in e.path) or '(arguments)'}: {e.message}"
            for e in errors
        ]
        return _text_result("Invalid arguments:\n" + "\n".join(details), is_error=True)

    try:
        data = tool.handler(ctx, arguments)
    except ToolError as e:
        logger.info(
            "care_mcp tool=%s user=%s outcome=error", name, ctx.user.external_id
        )
        payload = {"error": e.message}
        if e.data is not None:
            payload["details"] = e.data
        return _text_result(payload, is_error=True)
    logger.info("care_mcp tool=%s user=%s outcome=ok", name, ctx.user.external_id)
    return _text_result(data)


def handle_prompts_list(ctx, params):
    return {
        "prompts": [
            {
                "name": name,
                "title": prompt["title"],
                "description": prompt["description"],
                "arguments": prompt["arguments"],
            }
            for name, prompt in PROMPTS.items()
        ]
    }


def handle_prompts_get(ctx, params):
    name = params.get("name")
    prompt = PROMPTS.get(name)
    if prompt is None:
        raise JSONRPCError(INVALID_PARAMS, f"Unknown prompt: {name}")
    arguments = params.get("arguments") or {}
    missing = [
        a["name"]
        for a in prompt["arguments"]
        if a["required"] and not arguments.get(a["name"])
    ]
    if missing:
        raise JSONRPCError(INVALID_PARAMS, f"Missing arguments: {', '.join(missing)}")
    encounter_id = arguments.get("encounter_id")
    text = prompt["template"].format(
        patient_id=arguments.get("patient_id", ""),
        facility_id=arguments.get("facility_id", ""),
        encounter_clause=f" and encounter {encounter_id}" if encounter_id else "",
    )
    return {
        "description": prompt["description"],
        "messages": [{"role": "user", "content": {"type": "text", "text": text}}],
    }


METHODS = {
    "initialize": handle_initialize,
    "ping": lambda ctx, params: {},
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
    "prompts/list": handle_prompts_list,
    "prompts/get": handle_prompts_get,
}


def error_response(id_, code, message, data=None):
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": id_, "error": error}


def handle_message(ctx: ToolContext, message: Any) -> dict | None:  # noqa: PLR0911
    """Handle one JSON-RPC message. Returns None for notifications and responses."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return error_response(None, INVALID_REQUEST, "Invalid JSON-RPC 2.0 message.")

    method = message.get("method")
    if method is None:
        # A response to a server-initiated request; this server sends none.
        return None
    if not isinstance(method, str):
        return error_response(
            message.get("id"), INVALID_REQUEST, "method must be a string."
        )
    if "id" not in message:
        # Notifications (notifications/initialized, notifications/cancelled…)
        # need no reply, and this stateless server keeps nothing to update.
        return None

    id_ = message["id"]
    handler = METHODS.get(method)
    if handler is None:
        return error_response(id_, METHOD_NOT_FOUND, f"Method not found: {method}")
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return error_response(id_, INVALID_PARAMS, "params must be an object.")
    try:
        result = handler(ctx, params)
    except JSONRPCError as e:
        return error_response(id_, e.code, e.message, e.data)
    except Exception:
        logger.exception("care_mcp: %s failed", method)
        return error_response(id_, INTERNAL_ERROR, "Internal error.")
    return {"jsonrpc": "2.0", "id": id_, "result": result}
