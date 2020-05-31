import re

from rest_framework import filters


class ReplaceFieldsOrderingFilter(filters.OrderingFilter):
    def get_ordering(self, request, queryset, view):
        params = request.query_params.get(self.ordering_param)
        related_ordering_fields_map = getattr(view, "related_ordering_fields_map", None)
        if params:
            fields = []
            for field in [param.strip() for param in params.split(",")]:
                if field.lstrip("-") in related_ordering_fields_map:
                    if field[0] == "-":
                        fields.append("-" + related_ordering_fields_map[field.lstrip("-")])
                    else:
                        fields.append(related_ordering_fields_map[field.lstrip("-")])
                else:
                    fields.append(field)
            ordering = self.remove_invalid_fields(queryset, fields, view, request)
            if ordering:
                return ordering

        return self.get_default_ordering(view)

    def get_valid_fields(self, queryset, view, context={}):
        related_ordering_fields_map = getattr(view, "related_ordering_fields_map", None)
        valid_fields = getattr(view, "ordering_fields", self.ordering_fields)
        valid_fields = [
            related_ordering_fields_map[field] if (field in related_ordering_fields_map.keys()) else field
            for field in valid_fields
        ]
        valid_fields = [(item, item) if isinstance(item, str) else item for item in valid_fields]
        return valid_fields
