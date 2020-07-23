from django.db import transaction
from django.db.models.query_utils import Q
from django_filters import rest_framework as filters
from dry_rest_permissions.generics import DRYPermissionFiltersBase, DRYPermissions
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from care.facility.api.serializers.patient_icmr import PatientICMRSerializer
from care.facility.api.serializers.shifting import ShiftingDetailSerializer, ShiftingSerializer
from care.facility.models import PatientConsultation, PatientRegistration, PatientSample, User, ShiftingRequest
from care.facility.models.patient_icmr import PatientSampleICMR


class ShiftingFilterBackend(DRYPermissionFiltersBase):
    def filter_queryset(self, request, queryset, view):
        if request.user.is_superuser:
            pass
        else:
            q_objects = Q(orgin_facility__users__id__exact=request.user.id)
            q_objects |= Q(shifting_approving_facility__users__id__exact=request.user.id)
            q_objects |= Q(assigned_facility__users__id__exact=request.user.id)
            if request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
                q_objects |= Q(orgin_facility__state=request.user.state)
                q_objects |= Q(shifting_approving_facility__state=request.user.state)
                q_objects |= Q(assigned_facility__state=request.user.state)
            elif request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
                q_objects |= Q(orgin_facility__district=request.user.district)
                q_objects |= Q(shifting_approving_facility__district=request.user.district)
                q_objects |= Q(assigned_facility__district=request.user.district)
            queryset = queryset.filter(q_objects).distinct("id")
        return queryset


class ShiftingFilterSet(filters.FilterSet):
    status = filters.ChoiceFilter(choices=ShiftingRequest.STATUS_CHOICES)
    facility = filters.UUIDFilter(field_name="facility__external_id")
    orgin_facility = filters.UUIDFilter(field_name="orgin_facility__external_id")
    shifting_approving_facility = filters.UUIDFilter(field_name="shifting_approving_facility__external_id")
    assigned_facility = filters.UUIDFilter(field_name="assigned_facility__external_id")
    emergency = filters.BooleanFilter(field_name="emergency")
    is_up_shift = filters.BooleanFilter(field_name="is_up_shift")


class ShiftingViewSet(viewsets.ModelViewSet):
    serializer_class = ShiftingSerializer
    lookup_field = "external_id"
    queryset = ShiftingRequest.objects.all()  # Get Related Fields also here TODO
    permission_classes = (IsAuthenticated,)
    filter_backends = (
        ShiftingFilterBackend,
        filters.DjangoFilterBackend,
    )
    filterset_class = ShiftingFilterSet

    def get_serializer_class(self):
        serializer_class = self.serializer_class
        if self.action == "retrieve":
            serializer_class = ShiftingDetailSerializer
        return serializer_class
