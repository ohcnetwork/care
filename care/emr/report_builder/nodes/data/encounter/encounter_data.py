from care.emr.registries.report_node.report_node_registry import ReportNodeRegistry
from care.emr.report_builder.nodes.base import NodeType, ReportBaseNode


class EncounterDataNode(ReportBaseNode):
    TYPE = NodeType.display
    NAME = "encounter_data"

    OPTIONS = [
        "encounter_class",
        "encounter_priority",
        "encounter_status",
    ]

    def construct_data(self):
        encounter = self.context["encounter"]
        return {
            "encounter_class": encounter.encounter_class,
            "encounter_priority": encounter.priority,
            "encounter_status": encounter.status,
        }

    def _render_to_html(self):
        import logging

        logging.info(self.context)
        if "datapoint" in self.properties:
            return self.construct_data()[self.properties["datapoint"]]
        return ""


ReportNodeRegistry.register(EncounterDataNode)
