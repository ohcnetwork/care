from care.emr.registries.report_node.report_node_registry import ReportNodeRegistry
from care.emr.report_builder.nodes.base import NodeType, ReportBaseNode


class H1Node(ReportBaseNode):
    NAME = "h1"
    TYPE = NodeType.functional

    def _render_to_html(self):
        return f"<h1>{self.render_children()}</h1>"


ReportNodeRegistry.register(H1Node)
