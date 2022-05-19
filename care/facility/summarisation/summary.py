from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.facility import FacilitySerializer
from care.facility.models import FacilityRelatedSummary


class FacilitySummarySerializer(serializers.ModelSerializer):
    facility = FacilitySerializer()

    class Meta:
        model = FacilityRelatedSummary
        exclude = (
            "id",
            "s_type",
        )


class FacilitySummaryFilter(filters.FilterSet):
    start_date = filters.DateFilter(field_name="created_date", lookup_expr="gte")
    end_date = filters.DateFilter(field_name="created_date", lookup_expr="lte")
    facility = filters.UUIDFilter(field_name="facility__external_id")
    district = filters.NumberFilter(field_name="facility__district__id")
    local_body = filters.NumberFilter(field_name="facility__local_body__id")
    state = filters.NumberFilter(field_name="facility__state__id")


class SummaryViewSet(ListModelMixin, GenericViewSet):
    lookup_field = "external_id"
    queryset = FacilityRelatedSummary.objects.all().order_by("-created_date")
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.DjangoFilterBackend]
    serializer_class = FacilitySummarySerializer
    filterset_class = FacilitySummaryFilter

    @method_decorator(cache_page(60 * 10))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
