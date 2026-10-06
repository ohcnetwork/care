"""Escape hatches: discover and call any Care API endpoint the user can reach."""

import re
from functools import cache

from django.urls import URLPattern, URLResolver, get_resolver

from care_mcp.dispatch import (
    API_PREFIX,
    BLOCKED_PATH_FRAGMENTS,
    BLOCKED_PATH_PREFIXES,
    PathNotAllowedError,
)
from care_mcp.tools.base import ToolError, raise_for_status, tool

READ_METHODS = {"get"}
WRITE_METHODS = {"post", "put", "patch", "delete"}


def _readable(pattern: str) -> str:
    """'^patient/(?P<patient_external_id>[^/.]+)/observation/$' → 'patient/{patient_external_id}/observation/'"""
    pattern = re.sub(r"\(\?P<(\w+)>[^)]*\)", r"{\1}", pattern)
    return pattern.replace("^", "").replace("$", "").replace("\\", "")


def _walk(patterns, prefix=""):
    for entry in patterns:
        if isinstance(entry, URLResolver):
            yield from _walk(entry.url_patterns, prefix + str(entry.pattern))
        elif isinstance(entry, URLPattern):
            yield prefix + str(entry.pattern), entry.callback


@cache
def api_endpoints() -> tuple[dict, ...]:
    endpoints = {}
    for raw, callback in _walk(get_resolver().url_patterns):
        path = "/" + _readable(raw)
        if not path.startswith(API_PREFIX) or "{format}" in path:
            continue
        lowered = path.lower()
        if lowered.startswith(BLOCKED_PATH_PREFIXES) or any(
            f in lowered for f in BLOCKED_PATH_FRAGMENTS
        ):
            continue
        actions = getattr(callback, "actions", None)
        if actions:
            methods = sorted(m.upper() for m in actions)
        else:
            view_class = getattr(callback, "cls", None) or getattr(
                callback, "view_class", None
            )
            methods = sorted(
                m.upper()
                for m in ("get", "post", "put", "patch", "delete")
                if view_class and hasattr(view_class, m)
            )
        entry = endpoints.setdefault(path, set())
        entry.update(methods)
    return tuple(
        {"path": path, "methods": sorted(methods)}
        for path, methods in sorted(endpoints.items())
    )


@tool(
    "list_api_endpoints",
    "List Care API endpoints",
    """
    List Care REST API endpoints (paths and HTTP methods), to use with
    care_api_get when no dedicated tool fits. Filter with a word such as
    "inventory", "schedule" or "location".
    """,
    {"contains": {"type": "string", "description": "Only paths containing this."}},
)
def list_api_endpoints(ctx, args):
    needle = (args.get("contains") or "").lower()
    endpoints = [e for e in api_endpoints() if needle in e["path"].lower()]
    if not ctx.allow_writes:
        endpoints = [
            {**e, "methods": [m for m in e["methods"] if m == "GET"]}
            for e in endpoints
            if "GET" in e["methods"]
        ]
    return {"count": len(endpoints), "endpoints": endpoints}


@tool(
    "care_api_get",
    "Read any Care API endpoint",
    """
    GET any Care API v1 path as the current user, e.g. "facility/{id}/location/".
    Use list_api_endpoints to find paths. List endpoints take limit and offset
    and return {"count", "results"}. The user's normal permissions apply.
    """,
    {
        "path": {
            "type": "string",
            "description": "Path under /api/v1/, e.g. 'facility/<id>/location/'.",
        },
        "query": {
            "type": "object",
            "description": "Query string parameters.",
            "additionalProperties": {
                "type": ["string", "number", "boolean", "array"],
            },
        },
    },
    ["path"],
)
def care_api_get(ctx, args):
    query = dict(args.get("query") or {})
    query.setdefault("limit", 20)
    try:
        return raise_for_status(ctx.api("get", args["path"], query=query))
    except PathNotAllowedError as e:
        raise ToolError(str(e)) from e


@tool(
    "care_api_request",
    "Write to the Care API",
    """
    Create, update or delete data through any Care API v1 endpoint as the current
    user (POST, PUT, PATCH or DELETE). This changes patient records: only call it
    when the user has clearly asked for the change, and read the record first.
    The request body uses the same JSON as Care's web app.
    """,
    {
        "method": {"enum": sorted(m.upper() for m in WRITE_METHODS)},
        "path": {"type": "string", "description": "Path under /api/v1/."},
        "body": {"type": "object", "description": "JSON request body."},
        "query": {
            "type": "object",
            "additionalProperties": {"type": ["string", "number", "boolean"]},
        },
    },
    ["method", "path"],
    read_only=False,
    destructive=True,
    idempotent=False,
    requires_writes=True,
)
def care_api_request(ctx, args):
    if not ctx.allow_writes:
        msg = "Writes are disabled for this MCP connection."
        raise ToolError(msg)
    try:
        result = ctx.api(
            args["method"], args["path"], query=args.get("query"), body=args.get("body")
        )
    except PathNotAllowedError as e:
        raise ToolError(str(e)) from e
    data = raise_for_status(result)
    return {"status_code": result.status_code, "data": data}
