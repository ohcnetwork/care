from care.emr.registries.report_node.report_node_registry import ReportNodeRegistry
from care.emr.report_builder.nodes.base import NodeType, ReportBaseNode


class ConstantNode(ReportBaseNode):
    NAME = "constant"
    TYPE = NodeType.display

    def _render_to_html(self):
        return self.properties.get("text", "")


ReportNodeRegistry.register(ConstantNode)
