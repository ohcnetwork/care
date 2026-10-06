from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from care_mcp.dispatch import APIResult, call_api

UUID = {"type": "string", "format": "uuid"}

PAGINATION = {
    "limit": {
        "type": "integer",
        "minimum": 1,
        "maximum": 100,
        "default": 20,
        "description": "Maximum number of results to return.",
    },
    "offset": {
        "type": "integer",
        "minimum": 0,
        "default": 0,
        "description": "Number of results to skip, for paging.",
    },
}

# Appended to tool errors so the model knows how to recover instead of guessing.
STATUS_HINTS = {
    400: "Care rejected the request as invalid; check the arguments.",
    401: "The caller is not authenticated.",
    403: (
        "The current user is not allowed to see this. For a patient's clinical "
        "records, pass the encounter_id of an encounter the user has access to."
    ),
    404: "Not found, or not visible to the current user.",
}


class ToolError(Exception):
    """An error the model should see as a failed tool result, not a protocol error."""

    def __init__(self, message: str, data: Any = None):
        super().__init__(message)
        self.message = message
        self.data = data


@dataclass
class ToolContext:
    user: Any
    allow_writes: bool = False

    def api(self, method, path, query=None, body=None) -> APIResult:
        return call_api(self.user, method, path, query=query, body=body)

    def get(self, path, query=None) -> Any:
        """GET a Care API path, raising ToolError unless it succeeds."""
        return raise_for_status(self.api("get", path, query=query))

    def post_read(self, path, body) -> Any:
        """POST to a read-only Care action (search, analyse)."""
        return raise_for_status(self.api("post", path, body=body))


def raise_for_status(result: APIResult) -> Any:
    if result.ok:
        return result.data
    hint = STATUS_HINTS.get(result.status_code, "")
    message = f"Care API returned {result.status_code}. {hint}".strip()
    raise ToolError(message, data=result.data)


@dataclass
class Tool:
    name: str
    title: str
    description: str
    input_schema: dict
    handler: Callable[[ToolContext, dict], Any]
    read_only: bool = True
    destructive: bool = False
    idempotent: bool = True
    requires_writes: bool = False
    annotations: dict = field(init=False)

    def __post_init__(self):
        self.annotations = {
            "title": self.title,
            "readOnlyHint": self.read_only,
            "destructiveHint": self.destructive,
            "idempotentHint": self.idempotent,
            "openWorldHint": False,
        }

    def definition(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": self.input_schema,
            "annotations": self.annotations,
        }


REGISTRY: dict[str, Tool] = {}


def tool(
    name: str,
    title: str,
    description: str,
    properties: dict | None = None,
    required: list[str] | None = None,
    *,
    paginated: bool = False,
    **options,
):
    """Register a function as an MCP tool."""
    schema_properties = dict(properties or {})
    if paginated:
        schema_properties.update(PAGINATION)
    schema = {
        "type": "object",
        "properties": schema_properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required

    def decorator(func):
        REGISTRY[name] = Tool(
            name=name,
            title=title,
            description=description.strip(),
            input_schema=schema,
            handler=func,
            **options,
        )
        return func

    return decorator


def page(args: dict) -> dict:
    return {"limit": args.get("limit", 20), "offset": args.get("offset", 0)}
