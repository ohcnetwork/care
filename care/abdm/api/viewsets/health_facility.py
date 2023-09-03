from celery import shared_task
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import status
from rest_framework.decorators import action
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


@shared_task
def register_health_facility_as_service(facility_external_id):
    health_facility = HealthFacility.objects.filter(
        facility__external_id=facility_external_id,
    ).first()

    if not health_facility:
        return False

    if health_facility.registered:
        return True

    response = Bridge().add_update_service(
        {
            "id": health_facility.hf_id,
            "name": health_facility.facility.name,
            "type": "HIP",
            "active": True,
            "alias": ["CARE_HIP"],
        },
    )

    if response.status_code == status.HTTP_200_OK:
        health_facility.registered = True
        health_facility.save()
        return True

    return False


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
    permission_classes = (IsAuthenticated, DRYPermissions)
    lookup_field = "facility__external_id"

    def get_queryset(self):
        queryset = self.queryset
        facilities = get_facility_queryset(self.request.user)
        return queryset.filter(facility__in=facilities)

    @action(detail=True, methods=["POST"])
    def register_service(self, request, facility__external_id):
        registered = register_health_facility_as_service(facility__external_id)

        return Response({"registered": registered})

    def perform_create(self, serializer):
        instance = serializer.save()
        register_health_facility_as_service.delay(instance.facility.external_id)

    def perform_update(self, serializer):
        serializer.validated_data["registered"] = False
        instance = serializer.save()
        register_health_facility_as_service.delay(instance.facility.external_id)
