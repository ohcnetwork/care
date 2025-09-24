from care.emr.report_builder.nodes.base import ReportBaseNode


class ReportNodeRegistry:
    _node_classes = {}

    @classmethod
    def register(cls, node_class) -> None:
        if not issubclass(node_class, ReportBaseNode):
            raise ValueError("The provided class is not a subclass of ReportBaseNode")
        cls._node_classes[node_class.NAME] = node_class

    @classmethod
    def get_node_class(cls, node_name):
        if node_name not in cls._node_classes:
            raise ValueError("Invalid Node Name")
        return cls._node_classes.get(node_name)

    @classmethod
    def get_all_node_classes(cls):
        return list(cls._node_classes.values())
