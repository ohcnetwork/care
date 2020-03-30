from django.db import transaction
from django_filters import rest_framework as filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from simple_history.utils import bulk_create_with_history

from care.facility.api.serializers.facility import FacilitySerializer, FacilityUpsertSerializer
from care.facility.api.serializers.patient import PatientListSerializer
from care.facility.api.viewsets import FacilityBaseViewset
from care.facility.models import Facility, FacilityCapacity, PatientRegistration


class FacilityFilter(filters.FilterSet):
    district = filters.NumberFilter(field_name="facilitylocalgovtbody__district_id")
    district_name = filters.CharFilter(field_name="facilitylocalgovtbody__district__name", lookup_expr="icontains")
    local_body = filters.NumberFilter(field_name="facilitylocalgovtbody__local_body_id")
    local_body_name = filters.CharFilter(field_name="facilitylocalgovtbody__local_body__name", lookup_expr="icontains")


class FacilityViewSet(FacilityBaseViewset, ListModelMixin):
    """Viewset for facility CRUD operations."""

    serializer_class = FacilitySerializer
    queryset = Facility.objects.filter(is_active=True).select_related("local_body", "district", "state")
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilityFilter

    def list(self, request, *args, **kwargs):
        """
        Facility List

        Supported filters
        - `district` - ID
        - `district_name` - supports for ilike match
        - `local_body` - ID
        - `local_body_name` - supports for ilike match
        """
        return super(FacilityViewSet, self).list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """
        Facility Create

        - `local_govt_body` is a read_only field
        - `local_body` is the field for local_body/ panchayath / municipality / corporation
        - `district` current supports only Kerala, will be changing when the UI is ready to support any district
        """
        return super(FacilityViewSet, self).create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """
        Facility Update

        - `local_govt_body` is a read_only field
        - `local_body` is the field for local_body / panchayath / municipality / corporation
        - `district` current supports only Kerala, will be changing when the UI is ready to support any district
        """
        return super(FacilityViewSet, self).update(request, *args, **kwargs)

    @action(methods=["POST"], detail=False)
    def bulk_upsert(self, request):
        """
        Upserts based on case insensitive name (after stripping off blank spaces) and district.
        Check serializer for more.

        Request:
        [
            {
                "name": "Name",
                "district": 1,
                "facility_type": 2,
                "address": "Address",
                "phone_number": "Phone",
                "capacity": [
                    {
                        "room_type": 0,
                        "total_capacity": "350",
                        "current_capacity": "350"
                    },
                    {
                        "room_type": 1,
                        "total_capacity": 0,
                        "current_capacity": 0
                    }
                ]
            }
        ]
        :param request:
        :return:
        """
        data = request.data
        if not isinstance(data, list):
            data = [data]

        serializer = FacilityUpsertSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)

        district_id = request.data[0]["district"]
        facilities = (
            Facility.objects.filter(district_id=district_id)
            .select_related("local_body", "district", "state", "created_by__district", "created_by__state")
            .prefetch_related("facilitycapacity_set")
        )

        facility_map = {f.name.lower(): f for f in facilities}
        facilities_to_update = []
        facilities_to_create = []

        for f in serializer.validated_data:
            f["district_id"] = f.pop("district")
            if f["name"].lower() in facility_map:
                facilities_to_update.append(f)
            else:
                f["created_by_id"] = request.user.id
                facilities_to_create.append(f)

        with transaction.atomic():
            capacity_create_objs = []
            for f in facilities_to_create:
                capacity = f.pop("facilitycapacity_set")
                f_obj = Facility.objects.create(**f)
                for c in capacity:
                    capacity_create_objs.append(FacilityCapacity(facility=f_obj, **c))
            for f in facilities_to_update:
                capacity = f.pop("facilitycapacity_set")
                f_obj = facility_map.get(f["name"].lower())
                changed = False
                for k, v in f.items():
                    if getattr(f_obj, k) != v:
                        setattr(f_obj, k, v)
                        changed = True
                if changed:
                    f_obj.save()
                capacity_map = {c.room_type: c for c in f_obj.facilitycapacity_set.all()}
                for c in capacity:
                    changed = False
                    if c["room_type"] in capacity_map:
                        c_obj = capacity_map.get(c["room_type"])
                        for k, v in c.items():
                            if getattr(c_obj, k) != v:
                                setattr(c_obj, k, v)
                                changed = True
                        if changed:
                            c_obj.save()
                    else:
                        capacity_create_objs.append(FacilityCapacity(facility=f_obj, **c))

            bulk_create_with_history(capacity_create_objs, FacilityCapacity, batch_size=500)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=["get"], detail=True)
    def patients(self, *args, **kwargs):
        queryset = PatientRegistration.objects.filter(facility_id=kwargs["pk"]).select_related(
            "local_body", "district", "state"
        )
        return self.get_paginated_response(PatientListSerializer(self.paginate_queryset(queryset), many=True).data)
