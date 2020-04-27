from datetime import timedelta

from celery.decorators import periodic_task
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from care.facility.api.serializers.facility import FacilitySerializer
from care.facility.api.serializers.facility_capacity import FacilityCapacitySerializer
from care.facility.models import FacilityCapacity
from care.users.models import User


class FacilityCapacitySummary(viewsets.ViewSet):

    permission_classes = (IsAuthenticated,)

    @method_decorator(cache_page(60 * 60 * 6))
    def list(self, request, format=None):

        if request.user.user_type < User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            return Response({}, status=status.HTTP_403_FORBIDDEN)

        possible_filter_params = ["state", "local_body", "district"]
        filter_params = {}
        for filter_query in possible_filter_params:
            if request.GET.get(filter_query, False):
                filter_params["facility__" + filter_query] = int(request.GET[filter_query])

        capacity_objects = FacilityCapacity.objects.filter(**filter_params).select_related(
            "facility", "facility__state", "facility__district", "facility__local_body"
        )
        capacity_summary = {}
        for capacity_object in capacity_objects:
            facility_id = capacity_object.facility.id
            if facility_id not in capacity_summary:
                capacity_summary[facility_id] = FacilitySerializer(capacity_object.facility).data
                capacity_summary[facility_id]["availability"] = []
            capacity_summary[facility_id]["availability"].append(FacilityCapacitySerializer(capacity_object).data)

        return Response(capacity_summary)


@periodic_task(run_every=timedelta(seconds=1500))
def facilitySummary():
    print("Testing Summarisation Again")
