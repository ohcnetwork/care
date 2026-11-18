from django_filters import rest_framework as filters

from care.emr.models import TagConfig
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)


class TagFilter(filters.FilterSet):
    category = filters.CharFilter(field_name="category")
    status = filters.CharFilter(field_name="status")


class QuerysetTagContextBuilder(QuerysetContextBuilder):
    filterset_class = TagFilter
    __filterset_backends__ = (filters.DjangoFilterBackend,)

    display = Field(
        display="Tag Display",
        preview_value="Example Tag",
        mapping=lambda t: t.display if t else None,
        description="Display the tag",
    )

    def get_context(self):
        return TagConfig.objects.filter(id__in=self.parent_context.tags)
