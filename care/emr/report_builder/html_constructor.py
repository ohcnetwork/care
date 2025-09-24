from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from care.emr.registries.report_node.report_node_registry import ReportNodeRegistry
from care.emr.report_builder.nodes.base import NodeType, ReportBaseNode

try:
    from care.emr.report_builder.nodes.structural.body import BodyNode
    from care.emr.report_builder.nodes.structural.structured_list import (
        StructuredListNode,
    )
except ImportError:
    BodyNode = None
    StructuredListNode = None


class ReportBaseContext(str, Enum):
    encounter = "encounter"
    invoice = "invoice"
    service_request = "service_request"
    diagnostic_report = "diagnostic_report"


class NodeData(BaseModel):
    name: str = Field(...)
    type: NodeType = Field(...)
    description: str = Field(default="")
    properties: dict[str, Any] = Field(default_factory=dict)
    children: list["NodeData"] = Field(default_factory=list)


class JSONValidationError(Exception):
    def __init__(self, message: str, validation_errors: list[dict] | None = None):
        super().__init__(message)
        self.validation_errors = validation_errors or []


class HTMLConstructor:
    @classmethod
    def get_node_class(cls, name: str) -> type[ReportBaseNode]:
        return ReportNodeRegistry.get_node_class(name)

    @classmethod
    def render_to_html(
        cls, report_config, context: ReportBaseContext, context_obj
    ) -> str:
        html_constructor = cls.convert_from_dict(report_config)
        return html_constructor.render_to_html({context: context_obj})

    @classmethod
    def convert_from_dict(cls, data: dict[str, Any]) -> ReportBaseNode:
        validated_data = NodeData.model_validate(data)
        return cls._convert_node_from_validated_data(validated_data, {})

    @classmethod
    def _convert_node_from_validated_data(
        cls, data: NodeData, base_cache: dict
    ) -> ReportBaseNode:
        node_class = cls.get_node_class(data.name)

        children = []
        for child_data in data.children:
            child_node = cls._convert_node_from_validated_data(child_data, base_cache)
            children.append(child_node)
        node_instance = node_class(
            properties=data.properties, children=children, cache=base_cache
        )

        return node_instance
