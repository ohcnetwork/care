from django.core.exceptions import ValidationError as DjangoValidationError
from django_filters import rest_framework as filters
from rest_framework import filters as drf_filters
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.fields import get_error_detail
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.bed import (
    AssetBedSerializer,
    BedSerializer,
    ConsultationBedSerializer,
)
from care.facility.models.bed import AssetBed, Bed, ConsultationBed
from care.facility.models.patient_base import BedTypeChoices
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities
from care.utils.filters.choicefilter import CareChoiceFilter, inverse_choices

inverse_bed_type = inverse_choices(BedTypeChoices)


class BedFilter(filters.FilterSet):
    facility = filters.UUIDFilter(field_name="facility__external_id")
    location = filters.UUIDFilter(field_name="location__external_id")
    bed_type = CareChoiceFilter(choice_dict=inverse_bed_type)


class BedViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    GenericViewSet,
):
    queryset = (
        Bed.objects.all()
        .select_related("facility", "location")
        .order_by("-created_date")
    )
    serializer_class = BedSerializer
    lookup_field = "external_id"
    filter_backends = (filters.DjangoFilterBackend, drf_filters.SearchFilter)
    permission_classes = [IsAuthenticated]
    search_fields = ["name"]
    filterset_class = BedFilter

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        if user.is_superuser:
            pass
        elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(facility__state=user.state)
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(facility__district=user.district)
        else:
            allowed_facilities = get_accessible_facilities(user)
            queryset = queryset.filter(facility__id__in=allowed_facilities)
        return queryset

    def destroy(self, request, *args, **kwargs):
        if request.user.user_type < User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            raise PermissionDenied()
        return super().destroy(request, *args, **kwargs)

    def handle_exception(self, exc):
        if isinstance(exc, DjangoValidationError):
            exc = DRFValidationError(detail=get_error_detail(exc))
        return super().handle_exception(exc)


class AssetBedFilter(filters.FilterSet):
    asset = filters.UUIDFilter(field_name="asset__external_id")
    bed = filters.UUIDFilter(field_name="bed__external_id")
    facility = filters.UUIDFilter(field_name="bed__facility__external_id")
    location = filters.UUIDFilter(field_name="bed__location__external_id")


class AssetBedViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    GenericViewSet,
):
    queryset = (
        AssetBed.objects.all().select_related("asset", "bed").order_by("-created_date")
    )
    serializer_class = AssetBedSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = AssetBedFilter
    lookup_field = "external_id"

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        if user.is_superuser:
            pass
        elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(bed__facility__state=user.state)
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(bed__facility__district=user.district)
        else:
            allowed_facilities = get_accessible_facilities(user)
            queryset = queryset.filter(bed__facility__id__in=allowed_facilities)
        return queryset


class ConsultationBedFilter(filters.FilterSet):
    consultation = filters.UUIDFilter(field_name="consultation__external_id")
    bed = filters.UUIDFilter(field_name="bed__external_id")


class ConsultationBedViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
    GenericViewSet,
):
    queryset = (
        ConsultationBed.objects.all()
        .select_related("consultation", "bed")
        .order_by("-created_date")
    )
    serializer_class = ConsultationBedSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ConsultationBedFilter
    lookup_field = "external_id"

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        if user.is_superuser:
            pass
        elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(bed__facility__state=user.state)
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(bed__facility__district=user.district)
        else:
            allowed_facilities = get_accessible_facilities(user)
            queryset = queryset.filter(bed__facility__id__in=allowed_facilities)
        return queryset
