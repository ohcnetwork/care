import json

from django.conf import settings
from django.db import models
from django_redis import get_redis_connection

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
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    valueset = models.ForeignKey("emr.ValueSet", on_delete=models.CASCADE)
    favorite_codes = models.JSONField(default=list)

    class Meta:
        unique_together = ("user", "valueset")

    MAX_FAVORITES = getattr(settings, "MAX_FAVORITES_FOR_VALUESET", 50)


class RecentViewsManager:
    _client = None
    MAX_RECENT_VIEW = getattr(settings, "MAX_RECENT_VIEW_FOR_VALUESET", 20)

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls._client = get_redis_connection("default")
        return cls._client

    @classmethod
    def get_recent_views(cls, cache_key):
        client = cls.get_client()
        items = client.lrange(cache_key, 0, -1)
        return [json.loads(item.decode()) for item in items]

    @classmethod
    def add_recent_view(cls, cache_key, code_obj):
        client = cls.get_client()
        code_json = json.dumps(code_obj)
        client.lrem(cache_key, 0, code_json)  # Remove if exists
        client.lpush(cache_key, code_json)  # Add new view at the front
        client.ltrim(cache_key, 0, cls.MAX_RECENT_VIEW - 1)  # Trim list

    @classmethod
    def remove_recent_view(cls, cache_key, code_obj):
        client = cls.get_client()
        code_json = json.dumps(code_obj)
        client.lrem(cache_key, 0, code_json)

    @classmethod
    def clear_recent_views(cls, cache_key):
        client = cls.get_client()
        client.delete(cache_key)
