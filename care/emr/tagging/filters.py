from uuid import UUID

from rest_framework.compat import coreapi, coreschema
from rest_framework.filters import BaseFilterBackend

from care.emr.tagging.base import SingleFacilityTagManager


class TagFilter(BaseFilterBackend):
    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name="tags",
                required=False,
                location="query",
                schema=coreschema.String(
                    title="Tags Filter",
                    description="Filter by tags",
                ),
            ),
            coreapi.Field(
                name="tags_behavior",
                required=False,
                location="query",
                schema=coreschema.String(
                    title="Tags Filter Behavior",
                    description="Either `all` or `any`",
                ),
            ),
        ]

    def get_schema_operation_parameters(self, view):
        return [
            {
                "name": "tags",
                "required": False,
                "in": "query",
                "description": "Filter by tags, Comma separated list of tag UUIDs",
                "schema": {
                    "type": "string",
                },
            },
            {
                "name": "tags_behavior",
                "required": False,
                "in": "query",
                "description": "Either `all` or `any`",
                "schema": {
                    "type": "string",
                },
            },
        ]


class SingleFacilityTagFilter(TagFilter):
    def filter_queryset(self, request, queryset, view):
        tags = request.query_params.get("tags", "").strip()
        tags_behavior = request.query_params.get("tags_behavior", "any")
        if not tags:
            return queryset
        tags = tags.split(",")
        tag_uuids = []
        for tag in tags:
            try:
                tag_uuids.append(UUID(tag))
            except ValueError:
                continue
        manager = SingleFacilityTagManager()
        tag_ids = []
        for tag_uuid in tag_uuids:
            tag_obj = manager.get_tag_from_external_id(tag_uuid)
            if tag_obj:
                tag_ids.append(tag_obj.id)
        if not tag_ids:
            return queryset.none()
        if tag_ids:
            if tags_behavior == "any":
                return queryset.filter(tags__overlap=tag_ids)
            if tags_behavior == "all":
                return queryset.filter(tags__contains=tag_ids)
        return queryset.none()
