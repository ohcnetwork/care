from care.emr.registries.report_node.report_node_registry import ReportNodeRegistry
from care.emr.report_builder.nodes.base import NodeType, ReportBaseNode


class StructuredListNode(ReportBaseNode):
    NAME = "structured_list"
    TYPE = NodeType.display

    def _render_to_html(self):
        return f"<ol {self.get_html_attributes()} >{self.render_children()}</ol>"


ReportNodeRegistry.register(StructuredListNode)
