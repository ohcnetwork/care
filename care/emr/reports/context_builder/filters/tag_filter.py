from django_filters import rest_framework as filters


class TagFilter(filters.FilterSet):
    category = filters.CharFilter(field_name="category")
    status = filters.CharFilter(field_name="status")
