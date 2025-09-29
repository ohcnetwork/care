from django.conf import settings
from django.core.cache import cache
from pydantic import BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from care.emr.models.favorites import (
    UserResourceFavorites,
    favorite_list_object_cache_key,
    favorite_lists_cache_key,
)
from care.emr.resources.favorites.spec import DEFAULT_FAVORITE_LIST
from care.facility.models.facility import Facility
from care.utils.shortcuts import get_object_or_404


class FavoriteRequest(BaseModel):
    favorite_list: str = DEFAULT_FAVORITE_LIST


class EMRFavoritesMixin:
    FAVORITE_RESOURCE = None

    def retrieve_facility_obj(self, obj):
        return obj.facility

    @action(detail=False, methods=["GET"])
    def favorite_lists(self, request, *args, **kwargs):
        user = self.request.user

        facility = kwargs.get("facility_external_id") or request.query_params.get(
            "facility"
        )
        if facility:
            facility = get_object_or_404(
                Facility.objects.only("id"), external_id=facility
            )

        favorite_lists = cache.get(
            favorite_lists_cache_key(user, self.FAVORITE_RESOURCE, facility)
        )
        if favorite_lists is None:
            favorite_list_obj = list(
                set(
                    UserResourceFavorites.objects.filter(
                        user=user,
                        resource_type=self.FAVORITE_RESOURCE,
                        facility=facility,
                    )
                    .order_by("-modified_date")
                    .values_list("favorite_list", flat=True)
                )
            )
            cache.set(
                favorite_lists_cache_key(user, self.FAVORITE_RESOURCE, facility),
                favorite_list_obj,
            )
        return Response({"lists": favorite_lists})

    @action(detail=True, methods=["POST"])
    def add_favorite(self, request, *args, **kwargs):
        request_data = FavoriteRequest(**request.data)
        favorite_list = request_data.favorite_list
        obj = self.get_object()
        user = self.request.user
        favorite_list_obj, _ = UserResourceFavorites.objects.get_or_create(
            user=user,
            favorite_list=favorite_list,
            resource_type=self.FAVORITE_RESOURCE,
            facility=self.retrieve_facility_obj(obj),
        )
        favorite_list_obj.favorites.insert(0, obj.id)
        # trim favorites list to max allowed
        favorite_list_obj.favorites = list(dict.fromkeys(favorite_list_obj.favorites))[
            : settings.MAX_FAVORITES_PER_LIST
        ]
        favorite_list_obj.save(update_fields=["favorites"])
        return Response({})

    @action(detail=True, methods=["POST"])
    def remove_favorite(self, request, *args, **kwargs):
        request_data = FavoriteRequest(**request.data)
        favorite_list = request_data.favorite_list
        obj = self.get_object()
        user = self.request.user
        facility = self.retrieve_facility_obj(obj)
        favorite_list_obj = UserResourceFavorites.objects.filter(
            user=user,
            favorite_list=favorite_list,
            resource_type=self.FAVORITE_RESOURCE,
            facility=facility,
        ).first()
        if not favorite_list_obj:
            raise ValidationError("Favorite List not found")
        favorite_list_obj_favorites = dict.fromkeys(favorite_list_obj.favorites)
        favorite_list_obj_favorites.pop(obj.id, None)
        if len(favorite_list_obj_favorites) == 0:
            cache.delete(
                favorite_lists_cache_key(user, self.FAVORITE_RESOURCE, facility)
            )
            cache.delete(
                favorite_list_object_cache_key(
                    user,
                    self.FAVORITE_RESOURCE,
                    facility,
                    favorite_list_obj.favorite_list,
                )
            )
            UserResourceFavorites.objects.filter(id=favorite_list_obj.id).delete()
            return Response({})
        favorite_list_obj.favorites = list(favorite_list_obj_favorites)
        favorite_list_obj.save(update_fields=["favorites"])
        return Response({})
