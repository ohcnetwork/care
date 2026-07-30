from care.emr.api.viewsets.base import EMRBaseViewSet, EMRListMixin, EMRRetrieveMixin
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

    def get_queryset(self):
        return DiagnosticReport.objects.filter(
            patient__phone_number=self.request.user.phone_number
        )
