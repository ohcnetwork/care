from django_filters import rest_framework as filters
from rest_framework.filters import OrderingFilter

from care.emr.api.viewsets.base import EMRBaseViewSet, EMRListMixin, EMRRetrieveMixin
from care.emr.api.viewsets.diagnostic_report import DiagnosticReportFilters
from care.emr.models.diagnostic_report import DiagnosticReport
from care.emr.resources.diagnostic_report.spec import (
    DiagnosticReportListSpec,
    DiagnosticReportRetrieveSpec,
)
from config.patient_otp_authentication import (
    JWTTokenPatientAuthentication,
    OTPAuthenticatedPermission,
)


class OTPDiagnosticReportViewSet(EMRRetrieveMixin, EMRBaseViewSet, EMRListMixin):
    authentication_classes = [JWTTokenPatientAuthentication]
    permission_classes = [OTPAuthenticatedPermission]
    database_model = DiagnosticReport
    pydantic_read_model = DiagnosticReportListSpec
    pydantic_retrieve_model = DiagnosticReportRetrieveSpec
    filterset_class = DiagnosticReportFilters
    ordering_fields = ["created_date", "modified_date"]
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]

    def get_queryset(self):
        return DiagnosticReport.objects.filter(
            patient__phone_number=self.request.user.phone_number
        )
