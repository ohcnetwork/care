from care.emr.reports.authorizers.encounter import EncounterReportAuthorizer
from care.emr.reports.report_authorizer_registry import ReportAuthorizerRegistry


class DischargeSummaryReportAuthorizer(EncounterReportAuthorizer):
    pass


ReportAuthorizerRegistry.register("discharge_summary", DischargeSummaryReportAuthorizer)
