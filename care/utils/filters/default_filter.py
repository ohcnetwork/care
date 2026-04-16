from django_filters import BooleanFilter
from django_filters.constants import EMPTY_VALUES


class DefaultBooleanFilter(BooleanFilter):
    """Filter to check if a field is null or not"""

    def __init__(self, *args, **kwargs):
        self.default_value = kwargs.pop("default")
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            value = self.default_value
        return super().filter(qs, value)
