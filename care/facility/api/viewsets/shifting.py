from django.conf import settings
from django.db.models.query_utils import Q
from django.utils.timezone import localtime, now
from django_filters import rest_framework as filters
from djqscsv import render_to_csv_response
from dry_rest_permissions.generics import DRYPermissionFiltersBase, DRYPermissions
from rest_framework import filters as rest_framework_filters
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.shifting import (
    ShiftingDetailSerializer,
    ShiftingSerializer,
    has_facility_permission,
)
from care.facility.models import (
    SHIFTING_STATUS_CHOICES,
    BREATHLESSNESS_CHOICES,
    PatientConsultation,
    ShiftingRequest,
    User,
)

from care.utils.cache.cache_allowed_facilities import get_accessible_facilities


def inverse_choices(choices):
    output = {}
    for choice in choices:
        output[choice[1]] = choice[0]
    return output


inverse_shifting_status = inverse_choices(SHIFTING_STATUS_CHOICES)
inverse_breathlessness_level = inverse_choices(BREATHLESSNESS_CHOICES)


class ShiftingFilterBackend(DRYPermissionFiltersBase):
    def filter_queryset(self, request, queryset, view):
        if request.user.is_superuser:
            pass
        else:
            if request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
                q_objects = Q(orgin_facility__state=request.user.state)
                q_objects |= Q(shifting_approving_facility__state=request.user.state)
                q_objects |= Q(assigned_facility__state=request.user.state)
                return queryset.filter(q_objects)
            elif request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
                q_objects = Q(orgin_facility__district=request.user.district)
                q_objects |= Q(shifting_approving_facility__district=request.user.district)
                q_objects |= Q(assigned_facility__district=request.user.district)
                return queryset.filter(q_objects)
            facility_ids = get_accessible_facilities(request.user)
            q_objects = Q(orgin_facility__id__in=facility_ids)
            q_objects |= Q(shifting_approving_facility__id__in=facility_ids)
            q_objects |= Q(assigned_facility__id__in=facility_ids, status__gte=20)
            q_objects |= Q(patient__facility__id__in=facility_ids)
            queryset = queryset.filter(q_objects)
        return queryset


class ShiftingFilterSet(filters.FilterSet):
    def get_breathlessness_level(
        self, queryset, field_name, value,
    ):
        if value:
            if value in inverse_breathlessness_level:
                return queryset.filter(status=inverse_breathlessness_level[value])
        return queryset

    def get_status(
        self, queryset, field_name, value,
    ):
        if value:
            if value in inverse_shifting_status:
                return queryset.filter(status=inverse_shifting_status[value])
        return queryset

    status = filters.CharFilter(method="get_status", field_name="status")
    breathlessness_level = filters.CharFilter(method="get_breathlessness_level", field_name="breathlessness_level")

    facility = filters.UUIDFilter(field_name="facility__external_id")
    patient = filters.UUIDFilter(field_name="patient__external_id")
    patient_name = filters.CharFilter(field_name="patient__name", lookup_expr="icontains")
    patient_phone_number = filters.CharFilter(field_name="patient__phone_number", lookup_expr="icontains")
    orgin_facility = filters.UUIDFilter(field_name="orgin_facility__external_id")
    shifting_approving_facility = filters.UUIDFilter(field_name="shifting_approving_facility__external_id")
    assigned_facility = filters.UUIDFilter(field_name="assigned_facility__external_id")
    emergency = filters.BooleanFilter(field_name="emergency")
    is_up_shift = filters.BooleanFilter(field_name="is_up_shift")
    is_kasp = filters.BooleanFilter(field_name="is_kasp")
    created_date = filters.DateFromToRangeFilter(field_name="created_date")
    modified_date = filters.DateFromToRangeFilter(field_name="modified_date")
    assigned_to = filters.NumberFilter(field_name="assigned_to__id")
    created_by = filters.NumberFilter(field_name="created_by__id")
    last_edited_by = filters.NumberFilter(field_name="last_edited_by__id")


class ShiftingViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, GenericViewSet
):
    serializer_class = ShiftingSerializer
    lookup_field = "external_id"
    queryset = ShiftingRequest.objects.all().select_related(
        "orgin_facility",
        "orgin_facility__ward",
        "orgin_facility__local_body",
        "orgin_facility__district",
        "orgin_facility__state",
        "shifting_approving_facility",
        "shifting_approving_facility__ward",
        "shifting_approving_facility__local_body",
        "shifting_approving_facility__district",
        "shifting_approving_facility__state",
        "assigned_facility",
        "assigned_facility__ward",
        "assigned_facility__local_body",
        "assigned_facility__district",
        "assigned_facility__state",
        "patient",
        "patient__ward",
        "patient__local_body",
        "patient__district",
        "patient__state",
        "patient__facility",
        "patient__facility__ward",
        "patient__facility__local_body",
        "patient__facility__district",
        "patient__facility__state",
        "assigned_to",
        "created_by",
        "last_edited_by",
    )
    ordering_fields = ["id", "created_date", "modified_date", "emergency"]

    permission_classes = (IsAuthenticated, DRYPermissions)
    filter_backends = (ShiftingFilterBackend, filters.DjangoFilterBackend, rest_framework_filters.OrderingFilter)
    filterset_class = ShiftingFilterSet

    def get_serializer_class(self):
        serializer_class = self.serializer_class
        if self.action == "retrieve":
            serializer_class = ShiftingDetailSerializer
        return serializer_class

    @action(detail=True, methods=["POST"])
    def transfer(self, request, *args, **kwargs):
        shifting_obj = self.get_object()
        if has_facility_permission(request.user, shifting_obj.shifting_approving_facility) or has_facility_permission(
            request.user, shifting_obj.assigned_facility
        ):
            if shifting_obj.assigned_facility and shifting_obj.status >= 70:
                if shifting_obj.patient:
                    patient = shifting_obj.patient
                    patient.facility = shifting_obj.assigned_facility
                    patient.is_active = True
                    patient.allow_transfer = False
                    patient.save()
                    shifting_obj.status = 80
                    shifting_obj.save(update_fields=["status"])
                    # Discharge from all other active consultations
                    PatientConsultation.objects.filter(patient=patient, discharge_date__isnull=True).update(
                        discharge_date=localtime(now())
                    )
                    return Response({"transfer": "completed"}, status=status.HTTP_200_OK)
        return Response({"error": "Invalid Request"}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        if settings.CSV_REQUEST_PARAMETER in request.GET:
            queryset = self.filter_queryset(self.get_queryset()).values(*ShiftingRequest.CSV_MAPPING.keys())
            return render_to_csv_response(
                queryset,
                field_header_map=ShiftingRequest.CSV_MAPPING,
                field_serializer_map=ShiftingRequest.CSV_MAKE_PRETTY,
            )
        return super(ShiftingViewSet, self).list(request, *args, **kwargs)
