from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import GenericViewSet
from care.emr.models import Schedule
from care.utils.shortcuts import get_object_or_404
from rest_framework.decorators import action
from care.emr.api.viewsets.base import EMRBaseViewSet, EMRRetrieveMixin
from care.facility.models.facility import Facility

# This import links the two files together
from care.emr.services.scheduling_service import AvailabilityService

# This matches the bottom half of your "After" photo
class SlotViewSet(EMRRetrieveMixin, EMRBaseViewSet):
    """
    Refactored ViewSet: Business logic moved to AvailabilityService.
    """

    @action(detail=False, methods=["POST"])
    def get_slots_for_day(self, request, *args, **kwargs):
        facility_external_id = self.kwargs["facility_external_id"]

        # The ViewSet now simply delegates work to the Service
        try:
            facility = get_object_or_404(Facility, external_id=facility_external_id)
            # CALLING THE SERVICE LAYER
            slots = AvailabilityService.get_available_slots(facility, request.data)
            return Response({"results": slots})

        except ValidationError as e:
            return Response({"error": str(e)}, status=400)
