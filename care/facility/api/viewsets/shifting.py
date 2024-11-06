from django.conf import settings
from django.db.models.query import QuerySet
from django.db.models.query_utils import Q
from django.utils.timezone import localtime, now
from django_filters import rest_framework as filters
from djqscsv import render_to_csv_response
from drf_spectacular.utils import extend_schema
from dry_rest_permissions.generics import DRYPermissionFiltersBase, DRYPermissions
from rest_framework import filters as rest_framework_filters
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.shifting import (
    REVERSE_SHIFTING_STATUS_CHOICES,
    ShiftingDetailSerializer,
    ShiftingListSerializer,
    ShiftingRequestCommentDetailSerializer,
    ShiftingRequestCommentListSerializer,
    ShiftingSerializer,
    has_facility_permission,
)
from care.facility.models import (
    BREATHLESSNESS_CHOICES,
    SHIFTING_STATUS_CHOICES,
    ConsultationBed,
    PatientConsultation,
    ShiftingRequest,
    ShiftingRequestComment,
    User,
)
from care.facility.models.patient_base import (
    DISEASE_STATUS_DICT,
    NewDischargeReasonEnum,
)
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities
from care.utils.filters.choicefilter import CareChoiceFilter
from care.utils.queryset.shifting import get_shifting_queryset


def inverse_choices(choices):
    output = {}
    for choice in choices:
        output[choice[1]] = choice[0]
    return output


inverse_shifting_status = inverse_choices(SHIFTING_STATUS_CHOICES)
inverse_breathlessness_level = inverse_choices(BREATHLESSNESS_CHOICES)


class ShiftingFilterBackend(DRYPermissionFiltersBase):
    def filter_queryset(self, request, queryset, view):
        return get_shifting_queryset(request.user)


class ShiftingFilterSet(filters.FilterSet):
    status = CareChoiceFilter(choice_dict=inverse_shifting_status)
    breathlessness_level = CareChoiceFilter(choice_dict=inverse_breathlessness_level)

    disease_status = CareChoiceFilter(
        choice_dict=DISEASE_STATUS_DICT, field_name="patient__disease_status"
    )
    facility = filters.UUIDFilter(field_name="facility__external_id")
    patient = filters.UUIDFilter(field_name="patient__external_id")
    patient_name = filters.CharFilter(
        field_name="patient__name", lookup_expr="icontains"
    )
    patient_phone_number = filters.CharFilter(
        field_name="patient__phone_number", lookup_expr="icontains"
    )
    origin_facility = filters.UUIDFilter(field_name="origin_facility__external_id")
    shifting_approving_facility = filters.UUIDFilter(
        field_name="shifting_approving_facility__external_id"
    )
    assigned_facility = filters.UUIDFilter(field_name="assigned_facility__external_id")
    emergency = filters.BooleanFilter(field_name="emergency")
    is_up_shift = filters.BooleanFilter(field_name="is_up_shift")
    is_kasp = filters.BooleanFilter(field_name="is_kasp")
    created_date = filters.DateFromToRangeFilter(field_name="created_date")
    modified_date = filters.DateFromToRangeFilter(field_name="modified_date")
    assigned_to = filters.NumberFilter(field_name="assigned_to__id")
    created_by = filters.NumberFilter(field_name="created_by__id")
    last_edited_by = filters.NumberFilter(field_name="last_edited_by__id")
    is_antenatal = filters.BooleanFilter(field_name="patient__is_antenatal")


class ShiftingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    serializer_class = ShiftingSerializer
    lookup_field = "external_id"
    queryset = ShiftingRequest.objects.all()
    ordering_fields = ["id", "created_date", "modified_date", "emergency"]

    permission_classes = (IsAuthenticated, DRYPermissions)
    filter_backends = (
        ShiftingFilterBackend,
        filters.DjangoFilterBackend,
        rest_framework_filters.OrderingFilter,
    )
    filterset_class = ShiftingFilterSet

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()
        if self.action == "list":
            queryset = queryset.select_related(
                "origin_facility",
                "shifting_approving_facility",
                "assigned_facility",
                "patient",
            )

        else:
            queryset = queryset.select_related(
                "origin_facility",
                "origin_facility__ward",
                "origin_facility__local_body",
                "origin_facility__district",
                "origin_facility__state",
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
        return queryset

    def get_serializer_class(self):
        serializer_class = self.serializer_class
        if self.action == "list":
            return ShiftingListSerializer
        if self.action == "retrieve":
            serializer_class = ShiftingDetailSerializer
        return serializer_class

    @extend_schema(tags=["shift"])
    @action(detail=True, methods=["POST"])
    def transfer(self, request, *args, **kwargs):
        shifting_obj = self.get_object()
        if (
            (
                has_facility_permission(
                    request.user, shifting_obj.shifting_approving_facility
                )
                or has_facility_permission(request.user, shifting_obj.assigned_facility)
            )
            and shifting_obj.assigned_facility
            and shifting_obj.status
            >= REVERSE_SHIFTING_STATUS_CHOICES["TRANSFER IN PROGRESS"]
            and shifting_obj.patient
        ):
            patient = shifting_obj.patient
            patient.facility = shifting_obj.assigned_facility
            patient.is_active = True
            patient.allow_transfer = False
            patient.save()
            shifting_obj.status = REVERSE_SHIFTING_STATUS_CHOICES["COMPLETED"]
            shifting_obj.save(update_fields=["status"])
            # Discharge from all other active consultations
            PatientConsultation.objects.filter(
                patient=patient, discharge_date__isnull=True
            ).update(
                discharge_date=localtime(now()),
                new_discharge_reason=NewDischargeReasonEnum.REFERRED,
            )
            ConsultationBed.objects.filter(
                consultation=patient.last_consultation,
                end_date__isnull=True,
            ).update(end_date=localtime(now()))

            return Response({"transfer": "completed"}, status=status.HTTP_200_OK)
        return Response(
            {"error": "Invalid Request"}, status=status.HTTP_400_BAD_REQUEST
        )

    def list(self, request, *args, **kwargs):
        if settings.CSV_REQUEST_PARAMETER in request.GET:
            queryset = (
                self.filter_queryset(self.get_queryset())
                .annotate(**ShiftingRequest.CSV_ANNOTATE_FIELDS)
                .values(*ShiftingRequest.CSV_MAPPING.keys())
            )
            return render_to_csv_response(
                queryset,
                field_header_map=ShiftingRequest.CSV_MAPPING,
                field_serializer_map=ShiftingRequest.CSV_MAKE_PRETTY,
            )
        return super().list(request, *args, **kwargs)


class ShifitngRequestCommentViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    serializer_class = ShiftingRequestCommentDetailSerializer
    lookup_field = "external_id"
    queryset = ShiftingRequestComment.objects.all().order_by("-created_date")

    permission_classes = (IsAuthenticated, DRYPermissions)

    def get_queryset(self):
        queryset = self.queryset.filter(
            request__external_id=self.kwargs.get("shift_external_id")
        )
        if self.request.user.is_superuser:
            pass
        else:
            if self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
                q_objects = Q(request__origin_facility__state=self.request.user.state)
                q_objects |= Q(
                    request__shifting_approving_facility__state=self.request.user.state
                )
                q_objects |= Q(
                    request__assigned_facility__state=self.request.user.state
                )
                return queryset.filter(q_objects)
            if self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
                q_objects = Q(
                    request__origin_facility__district=self.request.user.district
                )
                q_objects |= Q(
                    request__shifting_approving_facility__district=self.request.user.district
                )
                q_objects |= Q(
                    request__assigned_facility__district=self.request.user.district
                )
                return queryset.filter(q_objects)
            facility_ids = get_accessible_facilities(self.request.user)
            q_objects = Q(request__origin_facility__id__in=facility_ids)
            q_objects |= Q(request__shifting_approving_facility__id__in=facility_ids)
            q_objects |= Q(request__assigned_facility__id__in=facility_ids)
            q_objects |= Q(request__patient__facility__id__in=facility_ids)
            queryset = queryset.filter(q_objects)
        return queryset

    def get_request(self):
        queryset = get_shifting_queryset(self.request.user)
        queryset = queryset.filter(external_id=self.kwargs.get("shift_external_id"))
        return get_object_or_404(queryset)

    def perform_create(self, serializer):
        serializer.save(request=self.get_request())

    def get_serializer_class(self):
        if self.action == "list":
            return ShiftingRequestCommentListSerializer
        return ShiftingRequestCommentDetailSerializer
