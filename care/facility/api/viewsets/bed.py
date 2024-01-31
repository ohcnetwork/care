from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import OuterRef, Subquery
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters as drf_filters
from rest_framework import status
from rest_framework.decorators import action
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
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.bed import (
    AssetBedSerializer,
    BedSerializer,
    ConsultationBedSerializer,
    PatientAssetBedSerializer,
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        number_of_beds = serializer.validated_data.pop("number_of_beds", 1)
        # Bulk creating n number of beds
        if number_of_beds > 1:
            data = serializer.validated_data.copy()
            data.pop("name")
            beds = [
                Bed(
                    **data,
                    name=f"{serializer.validated_data['name']} {i+1}",
                )
                for i in range(number_of_beds)
            ]
            Bed.objects.bulk_create(beds)
            return Response(status=status.HTTP_201_CREATED)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def destroy(self, request, *args, **kwargs):
        if request.user.user_type < User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            raise PermissionDenied()
        instance = self.get_object()
        if instance.is_occupied:
            raise DRFValidationError(
                detail="Bed is occupied. Please discharge the patient first"
            )
        return super().destroy(request, *args, **kwargs)

    def handle_exception(self, exc):
        if isinstance(exc, DjangoValidationError):
            exc = DRFValidationError(detail=get_error_detail(exc))
        return super().handle_exception(exc)


class AssetBedFilter(filters.FilterSet):
    asset = filters.UUIDFilter(field_name="asset__external_id")
    bed = filters.UUIDFilter(field_name="bed__external_id")
    facility = filters.UUIDFilter(field_name="bed__facility__external_id")


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


class PatientAssetBedFilter(filters.FilterSet):
    location = filters.UUIDFilter(field_name="bed__location__external_id")
    asset_class = filters.CharFilter(field_name="asset__asset_class")
    bed_is_occupied = filters.BooleanFilter(method="filter_bed_is_occupied")

    def filter_bed_is_occupied(self, queryset, name, value):
        return queryset.filter(
            bed__id__in=Subquery(
                ConsultationBed.objects.filter(
                    bed__id=OuterRef("bed__id"), end_date__isnull=value
                ).values("bed__id")
            )
        )


@extend_schema_view(list=extend_schema(tags=["facility"]))
class PatientAssetBedViewSet(ListModelMixin, GenericViewSet):
    queryset = AssetBed.objects.select_related("asset", "bed").order_by("-created_date")
    serializer_class = PatientAssetBedSerializer
    filter_backends = (
        filters.DjangoFilterBackend,
        drf_filters.OrderingFilter,
    )
    filterset_class = PatientAssetBedFilter
    ordering_fields = [
        "bed__name",
        "created_date",
    ]

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
        return queryset.filter(
            bed__facility__external_id=self.kwargs["facility_external_id"]
        )


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
        .prefetch_related("assets")
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

    @extend_schema(
        description="Toggle patient privacy",
        responses={status.HTTP_200_OK: None},
        request=None,
        tags=["consultationbed"],
    )
    @action(detail=True, methods=["PATCH"])
    def toggle_patient_privacy(self, request, external_id):
        try:
            user: User = request.user
            consultation_bed: ConsultationBed = (
                self.get_queryset().filter(external_id=external_id).first()
            )

            if consultation_bed and (
                user.user_type == User.TYPE_VALUE_MAP["WardAdmin"]
                or user.user_type == User.TYPE_VALUE_MAP["LocalBodyAdmin"]
                or user.user_type == User.TYPE_VALUE_MAP["DistrictAdmin"]
                or user.user_type == User.TYPE_VALUE_MAP["StateAdmin"]
                or (
                    user.user_type == User.TYPE_VALUE_MAP["Doctor"]
                    and user.home_facility.external_id
                    == consultation_bed.bed.facility.external_id
                )
                or (
                    user.user_type == User.TYPE_VALUE_MAP["Staff"]
                    and user.home_facility.external_id
                    == consultation_bed.bed.facility.external_id
                )
            ):
                consultation_bed.privacy = not consultation_bed.privacy
                consultation_bed.save()
                return Response({"status": "success"}, status=status.HTTP_200_OK)
            raise PermissionDenied(
                detail="You do not have permission to perform this action"
            )
        except PermissionDenied as e:
            return Response({"message": e.detail}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
