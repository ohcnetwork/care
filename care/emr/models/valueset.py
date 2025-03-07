from django.core.cache import cache
from django.db import models, transaction

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
    MAX_RECENT_VIEW = 20
    MAX_FAVORITES = 50
    CACHE_TIMEOUT = 86400  # 24 hours

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

    def add_favorite(self, code_obj):
        favorites = self._get_cached_data("favorite_codes")

        if code_obj not in favorites:
            favorites.insert(0, code_obj)
            self._save_to_cache("favorite_codes", favorites)

    def remove_favorite(self, code_value):
        favorites = self._get_cached_data("favorite_codes")
        favorites = [
            c for c in favorites if c["code"] != code_value
        ]  # Remove matching code
        self._save_to_cache("favorite_codes", favorites)

    def get_favorites(self):
        return self._get_cached_data("favorite_codes")

    def clear_favorites(self):
        self._save_to_cache("favorite_codes", [])

    def add_recent_view(self, code_obj):
        recent_views = self._get_cached_data("recent_codes")

        recent_views = [c for c in recent_views if c["code"] != code_obj["code"]]
        recent_views.insert(0, code_obj)  # Add to the front
        recent_views = recent_views[: self.MAX_RECENT_VIEW]

        self._save_to_cache("recent_codes", recent_views)

    def get_recent_views(self):
        return self._get_cached_data("recent_codes")

    def clear_recent_views(self):
        self._save_to_cache("recent_codes", [])
