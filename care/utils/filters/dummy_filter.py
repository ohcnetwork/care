from django_filters import BooleanFilter


class DummyBooleanFilter(BooleanFilter):
    """Filter to check if a field is null or not"""

    def filter(self, qs, value):
        return qs
