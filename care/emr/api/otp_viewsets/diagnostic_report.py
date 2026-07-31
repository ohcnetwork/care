from django_filters import rest_framework as filters

from care.emr.api.otp_viewsets.base import QuerysetEnablerMixin
from care.emr.api.viewsets.base import EMRBaseViewSet, EMRListMixin, EMRRetrieveMixin
from care.emr.models.diagnostic_report import DiagnosticReport
from care.emr.resources.diagnostic_report.spec import (
    DiagnosticReportListSpec,
    DiagnosticReportRetrieveSpec,
)
from care.utils.filters.default_filter import DefaultOTPFilters
from config.patient_otp_authentication import (
    JWTTokenPatientAuthentication,
    OTPAuthenticatedPermission,
)


class OTPDiagnosticReportViewSet(
    QuerysetEnablerMixin, EMRRetrieveMixin, EMRBaseViewSet, EMRListMixin
):
    authentication_classes = [JWTTokenPatientAuthentication]
    permission_classes = [OTPAuthenticatedPermission]
    database_model = DiagnosticReport
    pydantic_read_model = DiagnosticReportListSpec
    pydantic_retrieve_model = DiagnosticReportRetrieveSpec
    filterset_class = DefaultOTPFilters
    filter_backends = [filters.DjangoFilterBackend]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(patient__phone_number=self.request.user.phone_number)
        )
