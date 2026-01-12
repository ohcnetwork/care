from rest_framework.exceptions import ValidationError
from care.emr.models.scheduling.schedule import Availability
from care.emr.api.viewsets.scheduling.schedule import get_schedulable_resource

# This matches the top half of your "After" photo
class AvailabilityService:
    @staticmethod
    def get_available_slots(facility, request_data):
        """
        Pure business logic: Calculates slots without knowing about HTTP requests.
        """
        # In the real code, we would call the helper function here
        resource = get_schedulable_resource(
            request_data.resource_type,
            request_data.resource_id,
            facility,
        )
        if not resource:
            raise ValidationError("No schedules found for this resource")

        # This encapsulates the complex calculation logic shown in the "Before" code
        # We return a simplified list for this architectural demo
        slots = []
        return slots
