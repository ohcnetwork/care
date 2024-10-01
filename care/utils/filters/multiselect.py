from django_filters import Filter


class MultiSelectFilter(Filter):
    def filter(self, qs, value):
        if not value:
            return qs
        if not self.field_name:
            return None
        values_list = value.split(",")
        filters = {self.field_name + "__in": values_list}
        return qs.filter(**filters)
