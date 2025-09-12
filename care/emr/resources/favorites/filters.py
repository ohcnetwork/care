from rest_framework.compat import coreapi, coreschema
from rest_framework.filters import BaseFilterBackend

from care.emr.models.favorites import UserResourceFavorites
from care.facility.models.facility import Facility
from care.utils.shortcuts import get_object_or_404


class FavoritesFilter(BaseFilterBackend):
    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name="favorite_list",
                required=False,
                location="query",
                schema=coreschema.String(
                    title="Favorite List",
                    description="Filter by favorite list",
                ),
            ),
        ]

    def get_schema_operation_parameters(self, view):
        return [
            {
                "name": "favorite_list",
                "required": False,
                "in": "query",
                "description": "Filter by favorite list",
                "schema": {
                    "type": "string",
                },
            }
        ]

    def filter_queryset(self, request, queryset, view):
        favorite_list = request.query_params.get("favorite_list")
        facility = request.query_params.get("facility")
        if not favorite_list:
            return queryset
        if facility:
            facility = get_object_or_404(
                Facility.objects.only("id"), external_id=facility
            )
        else:
            facility = None
        favorites_objs = UserResourceFavorites.objects.filter(
            user=request.user,
            favorite_list=favorite_list,
            resource_type=view.FAVORITE_RESOURCE,
        )
        if facility:
            favorites_objs = favorites_objs.filter(facility=facility)
        else:
            favorites_objs = favorites_objs.filter(facility__is_null=True)
        favorites_obj = favorites_objs.first()
        if not favorites_obj:
            return queryset.none()
        return queryset.filter(id__in=favorites_obj.favorites)
