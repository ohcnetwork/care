from django_filters import BooleanFilter


class NullFilter(BooleanFilter):
    """Filter to check if a field is null or not"""

    def filter(self, qs, value):
        if value is None:
            return qs
        if not self.field_name:
            return qs
        filters = {self.field_name + "__isnull": bool(value)}
        if self.exclude:
            return qs.exclude(**filters)
        return qs.filter(**filters)
