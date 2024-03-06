import re

from celery import shared_task
from django.conf import settings
from dry_rest_permissions.generics import DRYPermissions
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
from care.abdm.utils.api_call import Facility
from care.utils.queryset.facility import get_facility_queryset


@shared_task
def register_health_facility_as_service(facility_external_id):
    health_facility = HealthFacility.objects.filter(
        facility__external_id=facility_external_id
    ).first()

    if not health_facility:
        return [False, "Health Facility Not Found"]

    if health_facility.registered:
        return [True, None]

    clean_facility_name = re.sub(r"[^A-Za-z0-9 ]+", " ", health_facility.facility.name)
    clean_facility_name = re.sub(r"\s+", " ", clean_facility_name).strip()
    hip_name = settings.HIP_NAME_PREFIX + clean_facility_name + settings.HIP_NAME_SUFFIX
    response = Facility().add_update_service(
        {
            "facilityId": health_facility.hf_id,
            "facilityName": hip_name,
            "HRP": [
                {
                    "bridgeId": settings.ABDM_CLIENT_ID,
                    "hipName": hip_name,
                    "type": "HIP",
                    "active": True,
                    "alias": ["CARE_HIP"],
                }
            ],
        }
    )

    if response.status_code == 200:
        data = response.json()[0]

        if "error" in data:
            if (
                data["error"].get("code") == "2500"
                and settings.ABDM_CLIENT_ID in data["error"].get("message")
                and "already associated" in data["error"].get("message")
            ):
                health_facility.registered = True
                health_facility.save()
                return [True, None]

            return [
                False,
                data["error"].get("message", "Error while registering HIP as service"),
            ]

        if "servicesLinked" in data:
            health_facility.registered = True
            health_facility.save()
            return [True, None]

    return [False, None]


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
        [registered, error] = register_health_facility_as_service(facility__external_id)

        if error:
            return Response({"detail": error}, status=400)

        return Response({"registered": registered})

    def perform_create(self, serializer):
        instance = serializer.save(
            created_by=self.request.user, updated_by=self.request.user
        )
        register_health_facility_as_service.delay(instance.facility.external_id)

    def perform_update(self, serializer):
        serializer.validated_data["registered"] = False
        instance = serializer.save(updated_by=self.request.user)
        register_health_facility_as_service.delay(instance.facility.external_id)
