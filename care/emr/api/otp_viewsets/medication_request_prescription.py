from django_filters import rest_framework as filters

from care.emr.api.viewsets.base import EMRBaseViewSet, EMRListMixin, EMRRetrieveMixin
from care.emr.api.viewsets.medication_request_prescription import (
    MedicationRequestPrescriptionFilter,
)
from care.emr.models.medication_request import MedicationRequestPrescription
from care.emr.resources.medication.request_prescription.spec import (
    MedicationRequestPrescriptionReadSpec,
    MedicationRequestPrescriptionRetrieveMedicationsSpec,
)
from config.patient_otp_authentication import (
    JWTTokenPatientAuthentication,
    OTPAuthenticatedPermission,
)


class OTPMedicationRequestPrescriptionViewSet(
    EMRRetrieveMixin, EMRBaseViewSet, EMRListMixin
):
    authentication_classes = [JWTTokenPatientAuthentication]
    permission_classes = [OTPAuthenticatedPermission]
    database_model = MedicationRequestPrescription
    pydantic_read_model = MedicationRequestPrescriptionReadSpec
    pydantic_retrieve_model = MedicationRequestPrescriptionRetrieveMedicationsSpec
    filterset_class = MedicationRequestPrescriptionFilter
    filter_backends = [filters.DjangoFilterBackend]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(patient__phone_number=self.request.user.phone_number)
        )
