from django_filters import BooleanFilter
from django_filters import rest_framework as filters
from django_filters.constants import EMPTY_VALUES

from care.utils.filters.multiselect import MultiSelectFilter


class DefaultBooleanFilter(BooleanFilter):
    """Filter to check if a field is null or not"""

    def __init__(self, *args, **kwargs):
        self.default_value = kwargs.pop("default")
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            value = self.default_value
        return super().filter(qs, value)


class DefaultOTPFilters(filters.FilterSet):
    patient = filters.UUIDFilter(field_name="patient__external_id")
    status = MultiSelectFilter(field_name="status")
    facility = filters.UUIDFilter(field_name="facility__external_id")
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    created_date = filters.DateTimeFromToRangeFilter()
