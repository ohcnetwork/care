from django.conf import settings
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import transaction
from django.db.models.query_utils import Q
from django_filters import rest_framework as filters
from djqscsv import render_to_csv_response
from dry_rest_permissions.generics import DRYPermissionFiltersBase, DRYPermissions
from rest_framework import filters as drf_filters
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from simple_history.utils import bulk_create_with_history

from care.facility.api.serializers.facility import (
    FacilityBasicInfoSerializer,
    FacilitySerializer,
)
from care.facility.api.serializers.patient import PatientListSerializer
from care.facility.models import (
    Facility,
    FacilityCapacity,
    FacilityPatientStatsHistory,
    HospitalDoctors,
    PatientRegistration,
    facility,
)
from care.users.api.serializers.user import UserBaseMinimumSerializer
from care.users.models import User
from config.utils import get_psql_search_tokens


class FacilityFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    facility_type = filters.NumberFilter(field_name="facility_type")
    district = filters.NumberFilter(field_name="district__id")
    district_name = filters.CharFilter(field_name="district__name", lookup_expr="icontains")
    local_body = filters.NumberFilter(field_name="local_body__id")
    local_body_name = filters.CharFilter(field_name="local_body__name", lookup_expr="icontains")
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

    queryset = Facility.objects.all().select_related("ward", "local_body", "district", "state")
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    filter_backends = (FacilityQSPermissions, filters.DjangoFilterBackend, drf_filters.SearchFilter)
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
        if request.user.is_superuser or request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            if not PatientRegistration.objects.filter(facility=self.get_object(), is_active=True).exists():
                return super().destroy(request, *args, **kwargs)
            else:
                return Response(
                    {"facility": "cannot delete facility with active patients"}, status=status.HTTP_403_FORBIDDEN
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
                pretty_mapping.update(FacilityPatientStatsHistory.CSV_MAKE_PRETTY.copy())
            queryset = self.filter_queryset(self.get_queryset()).values(*mapping.keys())
            return render_to_csv_response(queryset, field_header_map=mapping, field_serializer_map=pretty_mapping)

        return super(FacilityViewSet, self).list(request, *args, **kwargs)

    @action(methods=["GET"], detail=True)
    def get_users(self, request, external_id):
        user_type_filter = None
        if "user_type" in request.GET:
            if request.GET["user_type"] in User.TYPE_VALUE_MAP:
                user_type_filter = User.TYPE_VALUE_MAP[request.GET["user_type"]]
        facility = Facility.objects.filter(external_id=external_id).first()
        if not facility:
            return Response({"facility": "does not exist"}, status=status.HTTP_404_NOT_FOUND)
        users = facility.users.all()
        if user_type_filter:
            users = users.filter(user_type=user_type_filter)
        users = users.order_by("-last_login")
        data = UserBaseMinimumSerializer(users, many=True)
        return Response(data.data)

    # @action(methods=["POST"], detail=False)
    # def bulk_upsert(self, request):
    #     """
    #     DEPRACATED FROM 19/06/2021
    #     Upserts based on case insensitive name (after stripping off blank spaces) and district.
    #     Check serializer for more.

    #     Request:
    #     [
    #         {
    #             "name": "Name",
    #             "district": 1,
    #             "facility_type": 2,
    #             "address": "Address",
    #             "phone_number": "Phone",
    #             "capacity": [
    #                 {
    #                     "room_type": 0,
    #                     "total_capacity": "350",
    #                     "current_capacity": "350"
    #                 },
    #                 {
    #                     "room_type": 1,
    #                     "total_capacity": 0,
    #                     "current_capacity": 0
    #                 }
    #             ]
    #         }
    #     ]
    #     :param request:
    #     :return:
    #     """
    #     data = request.data
    #     if not isinstance(data, list):
    #         data = [data]

    #     serializer = FacilityUpsertSerializer(data=data, many=True)
    #     serializer.is_valid(raise_exception=True)

    #     district_id = request.data[0]["district"]
    #     facilities = (
    #         Facility.objects.filter(district_id=district_id)
    #         .select_related("local_body", "district", "state", "created_by__district", "created_by__state")
    #         .prefetch_related("facilitycapacity_set")
    #     )

    #     facility_map = {f.name.lower(): f for f in facilities}
    #     facilities_to_update = []
    #     facilities_to_create = []

    #     for f in serializer.validated_data:
    #         f["district_id"] = f.pop("district")
    #         if f["name"].lower() in facility_map:
    #             facilities_to_update.append(f)
    #         else:
    #             f["created_by_id"] = request.user.id
    #             facilities_to_create.append(f)

    #     with transaction.atomic():
    #         capacity_create_objs = []
    #         for f in facilities_to_create:
    #             capacity = f.pop("facilitycapacity_set")
    #             f_obj = Facility.objects.create(**f)
    #             for c in capacity:
    #                 capacity_create_objs.append(FacilityCapacity(facility=f_obj, **c))
    #         for f in facilities_to_update:
    #             capacity = f.pop("facilitycapacity_set")
    #             f_obj = facility_map.get(f["name"].lower())
    #             changed = False
    #             for k, v in f.items():
    #                 if getattr(f_obj, k) != v:
    #                     setattr(f_obj, k, v)
    #                     changed = True
    #             if changed:
    #                 f_obj.save()
    #             capacity_map = {c.room_type: c for c in f_obj.facilitycapacity_set.all()}
    #             for c in capacity:
    #                 changed = False
    #                 if c["room_type"] in capacity_map:
    #                     c_obj = capacity_map.get(c["room_type"])
    #                     for k, v in c.items():
    #                         if getattr(c_obj, k) != v:
    #                             setattr(c_obj, k, v)
    #                             changed = True
    #                     if changed:
    #                         c_obj.save()
    #                 else:
    #                     capacity_create_objs.append(FacilityCapacity(facility=f_obj, **c))

    #         bulk_create_with_history(capacity_create_objs, FacilityCapacity, batch_size=500)

    #     return Response(status=status.HTTP_204_NO_CONTENT)


class AllFacilityViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet,
):
    queryset = Facility.objects.all().select_related("local_body", "district", "state")
    serializer_class = FacilityBasicInfoSerializer
    filter_backends = (filters.DjangoFilterBackend, drf_filters.SearchFilter)
    filterset_class = FacilityFilter
    lookup_field = "external_id"
    search_fields = ["name", "district__name", "state__name"]

