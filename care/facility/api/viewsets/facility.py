from django.conf import settings
from django_filters import rest_framework as filters
from djqscsv import render_to_csv_response
from dry_rest_permissions.generics import DRYPermissionFiltersBase, DRYPermissions
from rest_framework import filters as drf_filters
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from care.facility.api.serializers.facility import (
    FacilityBasicInfoSerializer,
    FacilitySerializer,
    FacilityImageUploadSerializer
)
from care.facility.models import (
    Facility,
    FacilityCapacity,
    FacilityPatientStatsHistory,
    HospitalDoctors,
    PatientRegistration
)
from care.users.models import User


class FacilityFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    facility_type = filters.NumberFilter(field_name="facility_type")
    district = filters.NumberFilter(field_name="district__id")
    district_name = filters.CharFilter(
        field_name="district__name", lookup_expr="icontains"
    )
    local_body = filters.NumberFilter(field_name="local_body__id")
    local_body_name = filters.CharFilter(
        field_name="local_body__name", lookup_expr="icontains"
    )
    state = filters.NumberFilter(field_name="state__id")
    state_name = filters.CharFilter(field_name="state__name", lookup_expr="icontains")
    kasp_empanelled = filters.BooleanFilter(field_name="kasp_empanelled")


class FacilityQSPermissions(DRYPermissionFiltersBase):
    def filter_queryset(self, request, queryset, view):
        if request.user.is_superuser:
            pass
        elif request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(state=request.user.state)
        elif request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(district=request.user.district)
        else:
            queryset = queryset.filter(users__id__exact=request.user.id)

        return queryset


class FacilityViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Viewset for facility CRUD operations."""

    queryset = Facility.objects.all().select_related(
        "ward", "local_body", "district", "state"
    )
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    filter_backends = (
        FacilityQSPermissions,
        filters.DjangoFilterBackend,
        drf_filters.SearchFilter,
    )
    filterset_class = FacilityFilter
    lookup_field = "external_id"

    search_fields = ["name", "district__name", "state__name"]

    FACILITY_CAPACITY_CSV_KEY = "capacity"
    FACILITY_DOCTORS_CSV_KEY = "doctors"
    FACILITY_TRIAGE_CSV_KEY = "triage"

    def get_serializer_class(self):
        if self.request.query_params.get("all") == "true":
            return FacilityBasicInfoSerializer
        else:
            return FacilitySerializer

    def destroy(self, request, *args, **kwargs):
        if (
            request.user.is_superuser
            or request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
        ):
            if not PatientRegistration.objects.filter(
                facility=self.get_object(), is_active=True
            ).exists():
                return super().destroy(request, *args, **kwargs)
            else:
                return Response(
                    {"facility": "cannot delete facility with active patients"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response({"permission": "denied"}, status=status.HTTP_403_FORBIDDEN)

    def list(self, request, *args, **kwargs):
        if settings.CSV_REQUEST_PARAMETER in request.GET:
            mapping = Facility.CSV_MAPPING.copy()
            pretty_mapping = Facility.CSV_MAKE_PRETTY.copy()
            if self.FACILITY_CAPACITY_CSV_KEY in request.GET:
                mapping.update(FacilityCapacity.CSV_RELATED_MAPPING.copy())
                pretty_mapping.update(FacilityCapacity.CSV_MAKE_PRETTY.copy())
            elif self.FACILITY_DOCTORS_CSV_KEY in request.GET:
                mapping.update(HospitalDoctors.CSV_RELATED_MAPPING.copy())
                pretty_mapping.update(HospitalDoctors.CSV_MAKE_PRETTY.copy())
            elif self.FACILITY_TRIAGE_CSV_KEY in request.GET:
                mapping.update(FacilityPatientStatsHistory.CSV_RELATED_MAPPING.copy())
                pretty_mapping.update(
                    FacilityPatientStatsHistory.CSV_MAKE_PRETTY.copy()
                )
            queryset = self.filter_queryset(self.get_queryset()).values(*mapping.keys())
            return render_to_csv_response(
                queryset, field_header_map=mapping, field_serializer_map=pretty_mapping
            )

        return super(FacilityViewSet, self).list(request, *args, **kwargs)

    @action(methods=["POST", "DELETE"], detail=True, permission_classes=[IsAuthenticated, DRYPermissions])
    def cover_image(self, request, external_id):
        facility = self.get_object()
        if not facility:
            return Response({"facility": "does not exist"}, status=status.HTTP_404_NOT_FOUND)

        if request.method == "POST":
            serialized_data = FacilityImageUploadSerializer(facility, data=request.data)
            if serialized_data.is_valid():
                serialized_data.save()
                return Response(serialized_data.data)
            
            return Response(serialized_data.errors, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "DELETE":
            facility.cover_image_url = None
            facility.save()
            return Response(status=status.HTTP_204_NO_CONTENT)


class AllFacilityViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Facility.objects.all().select_related("local_body", "district", "state")
    serializer_class = FacilityBasicInfoSerializer
    filter_backends = (filters.DjangoFilterBackend, drf_filters.SearchFilter)
    filterset_class = FacilityFilter
    lookup_field = "external_id"
    search_fields = ["name", "district__name", "state__name"]
