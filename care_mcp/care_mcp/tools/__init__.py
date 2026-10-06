"""MCP tools. Importing this package registers every tool in REGISTRY.

Modules are imported in the order their tools should be listed to clients.
"""

# isort: off
from care_mcp.tools import directory
from care_mcp.tools import summary
from care_mcp.tools import clinical
from care_mcp.tools import generic

# isort: on
from care_mcp.tools.base import REGISTRY, Tool, ToolContext, ToolError

__all__ = [
    "REGISTRY",
    "Tool",
    "ToolContext",
    "ToolError",
    "clinical",
    "directory",
    "generic",
    "summary",
]
