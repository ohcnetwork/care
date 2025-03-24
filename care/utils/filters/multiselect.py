from django_filters import Filter


class MultiSelectFilter(Filter):
    def filter(self, qs, value):
        if not value:
            return qs
        if not self.field_name:
            return qs
        values_list = value.split(",")
        filters = {self.field_name + "__in": values_list}
        if self.exclude:
            return qs.exclude(**filters)
        return qs.filter(**filters)
