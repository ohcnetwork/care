from django.core.cache import cache
from rest_framework.compat import coreapi, coreschema
from rest_framework.filters import BaseFilterBackend

from care.emr.models.favorites import (
    UserResourceFavorites,
    favorite_list_object_cache_key,
)
from care.facility.models.facility import Facility
from care.utils.queryset.filters import sort_index
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
        if not favorite_list:
            return queryset

        facility = getattr(view, "kwargs", {}).get(
            "facility_external_id"
        ) or request.query_params.get("facility")
        if facility:
            facility = get_object_or_404(
                Facility.objects.only("id"), external_id=facility
            )

        favorites = cache.get(
            favorite_list_object_cache_key(
                request.user, view.FAVORITE_RESOURCE, facility, favorite_list
            )
        )
        if favorites is None:
            favorites_objs = UserResourceFavorites.objects.filter(
                user=request.user,
                favorite_list=favorite_list,
                resource_type=view.FAVORITE_RESOURCE,
                facility=facility,
            ).first()
            # setting the cache value as [] to ignore unnecessary cache misses
            favorites = favorites_objs.favorites if favorites_objs else []
            cache.set(
                favorite_list_object_cache_key(
                    request.user, view.FAVORITE_RESOURCE, facility, favorite_list
                ),
                favorites,
            )

        if not favorites:
            return queryset.none()
        return (
            queryset.filter(id__in=favorites)
            .annotate(favorite_order=sort_index("id", favorites))
            .order_by("favorite_order")
        )
