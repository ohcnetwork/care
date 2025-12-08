"""
Dummy filters are used to keep the filters in the swagger schema.
The filters will be manually handled in the business logic
"""

from django_filters import BooleanFilter, CharFilter, UUIDFilter


class DummyBooleanFilter(BooleanFilter):
    """Filter to check if a field is null or not"""

    def filter(self, qs, value):
        return qs


class DummyCharFilter(CharFilter):
    """Filter to check if a field is null or not"""

    def filter(self, qs, value):
        return qs


class DummyUUIDFilter(UUIDFilter):
    """Filter to check if a field is null or not"""

    def filter(self, qs, value):
        return qs
