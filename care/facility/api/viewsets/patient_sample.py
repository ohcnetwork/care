from django.db import transaction
from django_filters import rest_framework as filters
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from care.facility.api.mixins import UserAccessMixin
from care.facility.api.serializers.patient_sample import PatientSampleDetailSerializer, PatientSampleSerializer
from care.facility.models import PatientSample


class PatientSampleFilterSet(filters.FilterSet):
    district = filters.NumberFilter(field_name="facility__district_id")
    district_name = filters.CharFilter(
        field_name="facility__facilitylocalgovtbody__district__name", lookup_expr="icontains"
    )


class PatientSampleViewSet(UserAccessMixin, viewsets.ModelViewSet):
    serializer_class = PatientSampleSerializer
    queryset = PatientSample.objects.all()
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = PatientSampleFilterSet
    http_method_names = ["get", "post", "patch", "delete"]

    def get_serializer_class(self):
        serializer_class = self.serializer_class
        if self.action == "retrieve":
            serializer_class = PatientSampleDetailSerializer
        return serializer_class

    def list(self, request, *args, **kwargs):
        """
        Patient Sample List

        Available Filters
        - district - District ID
        - district_name - District name - case insensitive match
        """
        return super(PatientSampleViewSet, self).list(request, *args, **kwargs)

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        notes = validated_data.pop("notes", "create")
        with transaction.atomic():
            instance = self.get_serializer_class().create(validated_data)
            instance.patientsampleflow_set.create(
                status=validated_data["status"], notes=notes, created_by=self.request.user
            )
            return instance

    def perform_update(self, serializer):
        validated_data = serializer.validated_data
        notes = validated_data.pop("notes", "create")
        with transaction.atomic():
            instance = self.get_serializer_class().update(serializer.instancce, validated_data)
            instance.patientsampleflow_set.create(
                status=validated_data["status"], notes=notes, created_by=self.request.user
            )
            return instance
