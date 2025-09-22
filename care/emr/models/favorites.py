from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.db import models

from care.emr.models import EMRBaseModel
from care.facility.models.facility import Facility
from care.users.models import User


def favorite_lists_cache_key(user, resource_type, facility):
    return f"user_favorites_lists:{user.id}:{resource_type}:{facility.id if facility else '-'}"


def favorite_list_object_cache_key(user, resource_type, facility, favorite_list):
    return f"user_favorites_list_object:{user.id}:{resource_type}:{facility.id if facility else '-'}:{favorite_list}"


class UserResourceFavorites(EMRBaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    favorites = ArrayField(models.IntegerField(), default=list)
    favorite_list = models.CharField(max_length=255)
    resource_type = models.CharField(max_length=255)
    facility = models.ForeignKey(
        Facility, on_delete=models.CASCADE, null=True, blank=True
    )

    def refresh_cache(self, refresh_list=False):
        if refresh_list:
            favorites_obj = list(
                set(
                    self.__class__.objects.filter(
                        user_id=self.user_id,
                        resource_type=self.resource_type,
                        facility_id=self.facility_id,
                    )
                    .order_by("-modified_date")
                    .values_list("favorite_list", flat=True)
                )
            )
            cache.set(
                favorite_lists_cache_key(self.user, self.resource_type, self.facility),
                favorites_obj,
            )
        cache.set(
            favorite_list_object_cache_key(
                self.user, self.resource_type, self.facility, self.favorite_list
            ),
            self.favorites,
        )

    def save(self, *args, **kwargs):
        refresh_list = not self.pk
        super().save(*args, **kwargs)
        self.refresh_cache(refresh_list=refresh_list)
