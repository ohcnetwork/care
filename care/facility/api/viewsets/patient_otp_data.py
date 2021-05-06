from django.conf import settings
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.patient import (
    PatientDetailSerializer,
    PatientListSerializer,
)
from care.facility.models import PatientConsultation, PatientRegistration, PatientSearch
from care.users.models import User


from config.patient_otp_authentication import JWTTokenPatientAuthentication


class OTPPatientDataViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    authentication_classes = (JWTTokenPatientAuthentication,)

    lookup_field = "external_id"
    permission_classes = (IsAuthenticated,)
    queryset = PatientRegistration.objects.all()
    serializer_class = PatientDetailSerializer

    def get_queryset(self):
        is_otp_login = getattr(self.request.user, "is_alternative_login", False)
        queryset = self.queryset
        if is_otp_login:
            queryset = queryset.filter(phone_number=self.request.user.phone_number)
        else:
            queryset = queryset.none()
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return PatientListSerializer
        else:
            return self.serializer_class
