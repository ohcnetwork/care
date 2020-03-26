from django.db import transaction
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


class FacilityViewSet(FacilityBaseViewset, ListModelMixin):
    """Viewset for facility CRUD operations."""

    serializer_class = FacilitySerializer
    queryset = Facility.objects.filter(is_active=True)

    @action(methods=["POST"], detail=False)
    def bulk_upsert(self, request):
        """
        Upserts based on case insensitive name (after stripping off blank spaces) and district.
        Check serializer for more.

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
