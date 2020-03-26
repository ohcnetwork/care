from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from care.facility.api.mixins import UserAccessMixin
from care.facility.api.serializers.patient import (
    PatientDetailSerializer,
    PatientSerializer,
)
from care.facility.models import PatientRegistration


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
