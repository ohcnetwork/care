from django_filters import rest_framework as filters

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


class OTPDiagnosticReportFilters(filters.FilterSet):
    patient = filters.UUIDFilter(field_name="patient__external_id")
    status = filters.CharFilter(lookup_expr="iexact")
    facility = filters.UUIDFilter(field_name="facility__external_id")
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    created_date = filters.DateTimeFromToRangeFilter()


class OTPDiagnosticReportViewSet(EMRRetrieveMixin, EMRBaseViewSet, EMRListMixin):
    authentication_classes = [JWTTokenPatientAuthentication]
    permission_classes = [OTPAuthenticatedPermission]
    database_model = DiagnosticReport
    pydantic_read_model = DiagnosticReportListSpec
    pydantic_retrieve_model = DiagnosticReportRetrieveSpec
    filterset_class = OTPDiagnosticReportFilters
    filter_backends = [filters.DjangoFilterBackend]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(patient__phone_number=self.request.user.phone_number)
        )
