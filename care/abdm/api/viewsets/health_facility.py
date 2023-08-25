from django.shortcuts import get_object_or_404
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.abdm.api.serializers.health_facility import HealthFacilitySerializer
from care.abdm.models import HealthFacility
from care.abdm.utils.api_call import Bridge
from care.utils.queryset.facility import get_facility_queryset


class HealthFacilityViewSet(
    GenericViewSet,
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
):
    serializer_class = HealthFacilitySerializer
    model = HealthFacility
    queryset = HealthFacility.objects.all()
    permission_classes = (IsAuthenticated,)
    lookup_field = "facility__external_id"

    def get_queryset(self):
        queryset = self.queryset
        facilities = get_facility_queryset(self.request.user)
        return queryset.filter(facility__in=facilities)

    def get_facility(self, facility_external_id):
        facilities = get_facility_queryset(self.request.user)
        return get_object_or_404(facilities.filter(external_id=facility_external_id))

    def link_health_facility(self, hf_id, facility_id):
        facility = self.get_facility(facility_id)
        return Bridge().add_update_service(
            {
                "id": hf_id,
                "name": facility.name,
                "type": "HIP",
                "active": True,
                "alias": ["CARE_HIP"],
            }
        )

    def create(self, request, *args, **kwargs):
        if (
            self.link_health_facility(
                request.data["hf_id"], request.data["facility"]
            ).status_code
            == 200
        ):
            return super().create(request, *args, **kwargs)

        return Response({"message": "Error linking health facility"}, status=400)

    def update(self, request, *args, **kwargs):
        if (
            self.link_health_facility(
                request.data["hf_id"], kwargs["facility__external_id"]
            ).status_code
            == 200
        ):
            return super().update(request, *args, **kwargs)

        return Response({"message": "Error linking health facility"}, status=400)
