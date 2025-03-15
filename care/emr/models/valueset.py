import json
from functools import lru_cache

from django.conf import settings
from django.core.cache import cache
from django.db import models, transaction
from django_redis import get_redis_connection

from care.emr.fhir.resources.valueset import ValueSetResource
from care.emr.models import EMRBaseModel
from care.emr.resources.common.valueset import ValueSetCompose
from care.utils.lock import Lock


class ValueSet(EMRBaseModel):
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(default="")
    compose = models.JSONField(default=dict)
    status = models.CharField(max_length=255)
    is_system_defined = models.BooleanField(default=False)

    def create_composition(self):
        systems = {}
        compose = self.compose
        if type(self.compose) is dict:
            compose = ValueSetCompose(**self.compose)
        for include in compose.include:
            system = include.system
            if system not in systems:
                systems[system] = {"include": []}
            systems[system]["include"].append(include.model_dump(exclude_defaults=True))
        for exclude in compose.exclude:
            system = exclude.system
            if system not in systems:
                systems[system] = {"exclude": []}
            systems[system]["exclude"].append(exclude.model_dump(exclude_defaults=True))
        return systems

    def search(self, search="", count=10, display_language=None):
        systems = self.create_composition()
        results = []
        for system in systems:
            temp = ValueSetResource().filter(
                search=search, count=count, **systems[system]
            )
            if display_language:
                temp = temp.filter(display_language=display_language)
            results.extend(temp.search())
        return results

    def lookup(self, code):
        systems = self.create_composition()
        results = []
        for system in systems:
            results.append(ValueSetResource().filter(**systems[system]).lookup(code))
        return any(results)


@lru_cache(maxsize=1)
def get_cached_redis_client():
    return get_redis_connection("default")


class UserValueSetPreference(EMRBaseModel):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    valueset = models.ForeignKey("emr.ValueSet", on_delete=models.CASCADE)
    favorite_codes = models.JSONField(default=list)

    class Meta:
        unique_together = ("user", "valueset")

    CACHE_KEY_PREFIX = "user_valueset_code_prefs:"
    MAX_RECENT_VIEW = getattr(settings, "MAX_RECENT_VIEW_FOR_VALUESET", 20)
    MAX_FAVORITES = getattr(settings, "MAX_FAVORITES_FOR_VALUESET", 50)

    redis_client = get_cached_redis_client()

    def _get_cache_key(self, field_name):
        return f"{self.CACHE_KEY_PREFIX}{self.external_id}:{field_name}"

    def _get_or_set_favourites(self):
        cache_key = self._get_cache_key("favourites")
        with Lock(cache_key):
            favourites = cache.get(cache_key)
            if not favourites:
                favourites = self.favorite_codes
                cache.set(cache_key, favourites)
            return favourites

    def _saved_favourite_and_update_cache(self, favourites):
        self.favorite_codes = favourites
        with transaction.atomic(), Lock(self._get_cache_key("favourites")):
            cache.set(self._get_cache_key("favourites"), favourites)
            self.save(update_fields=["favorite_codes"])

    def get_favourites(self):
        return self._get_or_set_favourites()

    def add_favourite(self, code_obj):
        refreshed_instance = UserValueSetPreference.objects.select_for_update().get(
            pk=self.pk
        )
        favourites = refreshed_instance.favorite_codes

        if code_obj not in favourites:
            favourites.append(code_obj)
            self._saved_favourite_and_update_cache(favourites)

    def remove_favourite(self, code_value):
        refreshed_instance = UserValueSetPreference.objects.select_for_update().get(
            pk=self.pk
        )
        favourites = refreshed_instance.favorite_codes

        new_favourites = [c for c in favourites if c["code"] != code_value]

        if new_favourites != favourites:
            self._saved_favourite_and_update_cache(new_favourites)

    def clear_favourites(self):
        self._saved_favourite_and_update_cache([])

    @staticmethod
    def get_recent_views(cache_key):
        """Fetches recent views from Redis."""
        items = UserValueSetPreference.redis_client.lrange(cache_key, 0, -1)
        return [json.loads(item.decode("utf-8")) for item in items]

    @staticmethod
    def add_recent_view(cache_key, code_obj):
        """Adds a recent view entry in Redis."""
        code_json = json.dumps(code_obj)
        r = UserValueSetPreference.redis_client  # Use the class-level client
        r.lrem(cache_key, 0, code_json)  # Remove if already exists
        r.lpush(cache_key, code_json)  # Add to front
        r.ltrim(cache_key, 0, UserValueSetPreference.MAX_RECENT_VIEW - 1)  # Trim to max

    @staticmethod
    def remove_recent_view(cache_key, code_obj):
        """Removes a specific recent view from Redis."""
        code_json = json.dumps(code_obj)
        UserValueSetPreference.redis_client.lrem(cache_key, 0, code_json)

    @staticmethod
    def clear_recent_views(cache_key):
        """Clears all recent views from Redis."""
        UserValueSetPreference.redis_client.delete(cache_key)
