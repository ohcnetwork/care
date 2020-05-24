from django_filters import rest_framework as filters

from apps.patients import models as patients_models


class PatientTimelineFilter(filters.FilterSet):
    description = filters.CharFilter(field_name="description", lookup_expr="istartswith")

    class Meta:
        model = patients_models.PatientTimeLine
        fields = ("date", "description")
