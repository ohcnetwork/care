import datetime

from django.db import transaction
from django.db.models.query_utils import Q
from django.utils.timezone import make_aware
from django_filters import rest_framework as filters
from dry_rest_permissions.generics import DRYPermissionFiltersBase, DRYPermissions
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from care.facility.api.mixins import UserAccessMixin
from care.facility.api.serializers.patient_sample import PatientSampleDetailSerializer, PatientSampleSerializer
from care.facility.models import PatientSample, User, patient_data


class PatientSampleFilterBackend(DRYPermissionFiltersBase):
    def filter_queryset(self, request, queryset, view):
        if request.user.is_superuser:
            pass
        elif request.user.user_type < User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(
                Q(consultation__facility__district=request.user.district)
                | Q(patient__created_by=request.user)
                | Q(consultation__facility__created_by=request.user)
            )
        return queryset


class PatientSampleFilterSet(filters.FilterSet):
    district = filters.NumberFilter(field_name="consultation__facility__district_id")
    district_name = filters.CharFilter(field_name="consultation__facility__district__name", lookup_expr="icontains")
    status = filters.ChoiceFilter(choices=PatientSample.SAMPLE_TEST_FLOW_CHOICES)
    result = filters.ChoiceFilter(choices=PatientSample.SAMPLE_TEST_RESULT_CHOICES)


class PatientSampleViewSet(UserAccessMixin, viewsets.ModelViewSet):
    serializer_class = PatientSampleSerializer
    queryset = PatientSample.objects.all()
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    filter_backends = (
        PatientSampleFilterBackend,
        filters.DjangoFilterBackend,
    )
    filterset_class = PatientSampleFilterSet
    http_method_names = ["get", "post", "patch", "delete"]

    def get_serializer_class(self):
        serializer_class = self.serializer_class
        if self.action == "retrieve":
            serializer_class = PatientSampleDetailSerializer
        return serializer_class

    def get_queryset(self):
        queryset = super(PatientSampleViewSet, self).get_queryset()
        if self.kwargs.get("patient_pk") is not None:
            queryset = queryset.filter(patient_id=self.kwargs.get("patient_pk"))
        return queryset

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
        if self.kwargs.get("patient_pk") is not None:
            validated_data["patient_id"] = self.kwargs.get("patient_pk")
        notes = validated_data.pop("notes", "create")
        if "consultation_id" not in validated_data:
            try:
                validated_data["consultation"] = patient_data.PatientConsultation.objects.filter(
                    patient=validated_data["patient_id"]
                ).order_by("-id")[0]
            except:
                raise Exception("No Consultation Done")
        else:
            try:
                validated_data["consultation"] = patient_data.PatientConsultation.objects.filter(
                    id=validated_data["consultation_id"]
                )
            except:
                raise Exception("No Consultation Done")

        with transaction.atomic():
            instance = serializer.create(validated_data)
            instance.patientsampleflow_set.create(status=instance.status, notes=notes, created_by=self.request.user)
            return instance

    def perform_update(self, serializer):
        validated_data = serializer.validated_data
        notes = validated_data.pop("notes", f"updated by {self.request.user.get_username()}")
        with transaction.atomic():
            if validated_data.get("status") == PatientSample.SAMPLE_TEST_FLOW_MAP["SENT_TO_COLLECTON_CENTRE"]:
                validated_data["date_of_sample"] = make_aware(datetime.datetime.now())
            elif validated_data.get("result") is not None:
                validated_data["date_of_result"] = make_aware(datetime.datetime.now())
                validated_data["status"] = PatientSample.SAMPLE_TEST_FLOW_MAP["COMPLETED"]
            instance = serializer.update(serializer.instance, validated_data)
            instance.patientsampleflow_set.create(status=instance.status, notes=notes, created_by=self.request.user)
            return instance
