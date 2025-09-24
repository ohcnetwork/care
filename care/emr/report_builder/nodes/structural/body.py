from care.emr.registries.report_node.report_node_registry import ReportNodeRegistry
from care.emr.report_builder.nodes.base import NodeType, ReportBaseNode


class BodyNode(ReportBaseNode):
    NAME = "body"
    TYPE = NodeType.functional

    def _render_to_html(self):
        return f"<body>{self.render_children()}</body>"


ReportNodeRegistry.register(BodyNode)
