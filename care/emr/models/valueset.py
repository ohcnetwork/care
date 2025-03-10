from contextlib import contextmanager

from django.conf import settings
from django.core.cache import cache
from django.db import models, transaction
from django_redis import get_redis_connection
from redis.exceptions import LockError

from care.emr.fhir.resources.valueset import ValueSetResource
from care.emr.models import EMRBaseModel
from care.emr.resources.common.valueset import ValueSetCompose


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


class UserValueSetPreference(EMRBaseModel):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE)
    valueset = models.ForeignKey("emr.ValueSet", on_delete=models.CASCADE)
    favorite_codes = models.JSONField(default=list)
    recent_codes = models.JSONField(default=list)

    class Meta:
        unique_together = ("user", "valueset")

    CACHE_KEY_PREFIX = "user_valueset_code_prefs:"
    MAX_RECENT_VIEW = settings.VALUESET_MAX_RECENT_VIEWS
    MAX_FAVORITES = settings.VALUESET_MAX_FAVORITES
    CACHE_TIMEOUT = settings.VALUESET_PREFERENCE_CACHE_TIMEOUT
    REDIS_LOCK_TIMEOUT = getattr(settings, "VALUESET_PREFERENCE_REDIS_LOCK_TIMEOUT", 5)
    REDIS_ACQUIRE_TIMEOUT = getattr(
        settings, "VALUESET_PREFERENCE_REDIS_ACQUIRE_TIMEOUT", 7
    )

    def _get_cache_key(self, field_name):
        return f"{self.CACHE_KEY_PREFIX}{self.user.external_id}:{self.valueset.external_id}:{field_name}"

    def _get_cached_data(self, field_name):
        cache_key = self._get_cache_key(field_name)
        return cache.get_or_set(
            cache_key, lambda: getattr(self, field_name), self.CACHE_TIMEOUT
        )

    def _save_to_cache(self, field_name, data):
        setattr(self, field_name, data)
        with transaction.atomic():
            self.save(update_fields=[field_name])
            cache.set(self._get_cache_key(field_name), data, self.CACHE_TIMEOUT)

    @contextmanager
    def locked_field(self, field_name):
        redis_conn = get_redis_connection("default")
        lock_key = f"{self._get_cache_key(field_name)}:lock"
        lock = redis_conn.lock(lock_key, timeout=self.REDIS_LOCK_TIMEOUT)
        acquired = lock.acquire(
            blocking=True, blocking_timeout=self.REDIS_ACQUIRE_TIMEOUT
        )

        if not acquired:
            error = f"Error acquiring lock for {lock_key}"
            raise ValueError(error)

        try:
            yield
        finally:
            try:
                lock.release()  # This may raise exception if yield takes more time than timeout
            except LockError:
                pass

    def add_favorite(self, code_obj):
        with self.locked_field("favorite_codes"):
            # Refresh the model from database inside the lock
            refreshed_instance = UserValueSetPreference.objects.select_for_update().get(
                pk=self.pk
            )
            favorites = refreshed_instance.favorite_codes

            if code_obj not in favorites:
                favorites.insert(0, code_obj)
                if len(favorites) > self.MAX_FAVORITES:
                    favorites = favorites[: self.MAX_FAVORITES]

                refreshed_instance.favorite_codes = favorites
                refreshed_instance.save(update_fields=["favorite_codes"])
                # Update the instance and cache
                self.favorite_codes = favorites
                cache.set(
                    self._get_cache_key("favorite_codes"), favorites, self.CACHE_TIMEOUT
                )

    def remove_favorite(self, code_value):
        with self.locked_field("favorite_codes"):
            refreshed_instance = UserValueSetPreference.objects.select_for_update().get(
                pk=self.pk
            )
            favorites = refreshed_instance.favorite_codes

            favorites = [c for c in favorites if c["code"] != code_value]

            refreshed_instance.favorite_codes = favorites
            refreshed_instance.save(update_fields=["favorite_codes"])
            self.favorite_codes = favorites
            cache.set(
                self._get_cache_key("favorite_codes"), favorites, self.CACHE_TIMEOUT
            )

    def get_favorites(self):
        return self._get_cached_data("favorite_codes")

    def clear_favorites(self):
        with self.locked_field("favorite_codes"):
            refreshed_instance = UserValueSetPreference.objects.select_for_update().get(
                pk=self.pk
            )
            refreshed_instance.favorite_codes = []
            refreshed_instance.save(update_fields=["favorite_codes"])
            self.favorite_codes = []
            cache.set(self._get_cache_key("favorite_codes"), [], self.CACHE_TIMEOUT)

    def add_recent_view(self, code_obj):
        with self.locked_field("recent_codes"):
            refreshed_instance = UserValueSetPreference.objects.select_for_update().get(
                pk=self.pk
            )
            recent_views = refreshed_instance.recent_codes

            recent_views = [c for c in recent_views if c["code"] != code_obj["code"]]
            recent_views.insert(0, code_obj)  # Add to the front
            recent_views = recent_views[: self.MAX_RECENT_VIEW]

            refreshed_instance.recent_codes = recent_views
            refreshed_instance.save(update_fields=["recent_codes"])
            self.recent_codes = recent_views
            cache.set(
                self._get_cache_key("recent_codes"), recent_views, self.CACHE_TIMEOUT
            )

    def remove_recent_view(self, code_value):
        with self.locked_field("recent_codes"):
            refreshed_instance = UserValueSetPreference.objects.select_for_update().get(
                pk=self.pk
            )
            recent_views = refreshed_instance.recent_codes

            recent_views = [c for c in recent_views if c["code"] != code_value]

            refreshed_instance.recent_codes = recent_views
            refreshed_instance.save(update_fields=["recent_codes"])
            self.recent_codes = recent_views
            cache.set(
                self._get_cache_key("recent_codes"), recent_views, self.CACHE_TIMEOUT
            )

    def get_recent_views(self):
        return self._get_cached_data("recent_codes")

    def clear_recent_views(self):
        with self.locked_field("recent_codes"):
            refreshed_instance = UserValueSetPreference.objects.select_for_update().get(
                pk=self.pk
            )
            refreshed_instance.recent_codes = []
            refreshed_instance.save(update_fields=["recent_codes"])
            self.recent_codes = []
            cache.set(self._get_cache_key("recent_codes"), [], self.CACHE_TIMEOUT)
