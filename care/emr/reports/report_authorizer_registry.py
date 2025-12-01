from care.emr.reports.authorizers.base import BaseReportAuthorizer


class ReportAuthorizerRegistry:
    _registry: dict[str, type[BaseReportAuthorizer]] = {}

    @classmethod
    def register(cls, report_type: str, authorizer_class: type[BaseReportAuthorizer]):
        if report_type in cls._registry:
            msg = f"Report authorizer for '{report_type}' is already registered"
            raise ValueError(msg)

        if not issubclass(authorizer_class, BaseReportAuthorizer):
            msg = "Authorizer must be a subclass of BaseReportAuthorizer"
            raise ValueError(msg)

        cls._registry[report_type] = authorizer_class

    @classmethod
    def get(cls, report_type: str) -> type[BaseReportAuthorizer]:
        if report_type not in cls._registry:
            msg = f"No authorizer registered for report type: {report_type}"
            raise KeyError(msg)
        return cls._registry[report_type]

    @classmethod
    def is_registered(cls, report_type: str) -> bool:
        return report_type in cls._registry

    @classmethod
    def get_all_types(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def clear(cls):
        cls._registry.clear()
