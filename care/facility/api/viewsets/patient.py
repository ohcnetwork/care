from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from care.facility.api.mixins import UserAccessMixin
from care.facility.api.serializers.patient import PatientDetailSerializer, PatientSerializer
from care.facility.api.serializers.patient_consultation import PatientConsultationSerializer
from care.facility.models import PatientConsultation, PatientRegistration


class PatientFilterSet(filters.FilterSet):
    phone_number = filters.CharFilter(field_name="phone_number")


class PatientViewSet(UserAccessMixin, viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = PatientRegistration.objects.filter(deleted=False)
    serializer_class = PatientSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = PatientFilterSet

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PatientDetailSerializer
        else:
            return self.serializer_class

    @action(detail=True, methods=["get"])
    def history(self, request, *args, **kwargs):
        user = request.user
        queryset = PatientConsultation.objects.filter(patient__id=self.kwargs.get("pk"))
        if not user.is_superuser:
            queryset = queryset.filter(patient__created_by=user)
        return Response(data=PatientConsultationSerializer(queryset, many=True).data)
