from django.conf import settings
from pydantic import BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from care.emr.models.favorites import UserResourceFavorites
from care.emr.resources.favorites.spec import DEFAULT_FAVORITE_LIST


class FavoriteRequest(BaseModel):
    favorite_list: str = DEFAULT_FAVORITE_LIST


class EMRFavoritesMixin:
    FAVORITE_RESOURCE = None

    def retrieve_facility_obj(self, obj):
        return obj.facility

    @action(detail=False, methods=["GET"])
    def favorite_lists(self, request, *args, **kwargs):
        user = self.request.user
        favorites_obj = UserResourceFavorites.objects.filter(
            user=user, resource_type=self.FAVORITE_RESOURCE
        )
        return Response(
            {"lists": list(set(favorites_obj.values_list("favorite_list", flat=True)))}
        )

    @action(detail=True, methods=["POST"])
    def add_favorite(self, request, *args, **kwargs):
        obj = self.get_object()
        self.authorize_retrieve(obj)
        user = self.request.user
        request_data = FavoriteRequest(**request.data)
        favorite_list = request_data.favorite_list
        favorites_obj, _ = UserResourceFavorites.objects.get_or_create(
            user=user,
            favorite_list=favorite_list,
            resource_type=self.FAVORITE_RESOURCE,
            facility=self.retrieve_facility_obj(obj),
        )
        if len(favorites_obj.favorites) >= settings.MAX_FAVORITES_PER_LIST:
            raise ValidationError("Maximum number of favorites reached")
        favorites_obj.favorites.append(obj.id)
        favorites_obj.favorites = list(set(favorites_obj.favorites))
        favorites_obj.save(update_fields=["favorites"])
        return Response({})

    @action(detail=True, methods=["POST"])
    def remove_favorite(self, request, *args, **kwargs):
        obj = self.get_object()
        self.authorize_retrieve(obj)
        user = self.request.user
        request_data = FavoriteRequest(**request.data)
        favorite_list = request_data.favorite_list
        favorites_obj = UserResourceFavorites.objects.filter(
            user=user,
            favorite_list=favorite_list,
            resource_type=self.FAVORITE_RESOURCE,
            facility=self.retrieve_facility_obj(obj),
        ).first()
        if not favorites_obj:
            raise ValidationError("Favorite List not found")
        favorites_obj.favorites = [
            fav for fav in favorites_obj.favorites if fav != obj.id
        ]
        favorites_obj.favorites = list(set(favorites_obj.favorites))
        favorites_obj.save(update_fields=["favorites"])
        return Response({})
