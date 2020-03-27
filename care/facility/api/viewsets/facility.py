from django.db import transaction
from django_filters import rest_framework as filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response

from care.facility.api.serializers.facility import (
    FacilitySerializer,
    FacilityUpsertSerializer,
)
from care.facility.api.viewsets import FacilityBaseViewset
from care.facility.models import Facility


class FacilityFilter(filters.FilterSet):
    district = filters.NumberFilter(field_name="facilitylocalgovtbody__district_id")
    district_name = filters.CharFilter(field_name="facilitylocalgovtbody__district__name", lookup_expr="icontains")
    local_body = filters.NumberFilter(field_name="facilitylocalgovtbody__local_body_id")
    local_body_name = filters.CharFilter(field_name="facilitylocalgovtbody__local_body__name", lookup_expr="icontains")


class FacilityViewSet(FacilityBaseViewset, ListModelMixin):
    """Viewset for facility CRUD operations."""

    serializer_class = FacilitySerializer
    queryset = Facility.objects.filter(is_active=True)
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

        serializer.context["user"] = self.request.user
        with transaction.atomic():
            serializer.create(serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)
