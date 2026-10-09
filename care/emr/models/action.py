from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.db import models

from care.emr.models.base import EMRBaseModel

ACTION_CACHE_KEY = "action:cache:context:{context}:facility:{facility}"


class Action(EMRBaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField()
    action_context = models.CharField(max_length=255)
    actions = models.JSONField()
    facility = models.ForeignKey(
        "facility.Facility", on_delete=models.CASCADE, null=True, blank=True
    )
    performable = models.BooleanField(default=True)
    organization_cache = ArrayField(models.IntegerField(), default=list)
    internal_organization_cache = ArrayField(models.IntegerField(), default=list)

    def save(self, *args, **kwargs):
        self.invalidate_cache()
        super().save(*args, **kwargs)

    def invalidate_instance_cache(self):
        cache.delete(ACTION_CACHE_KEY.format(context=self.action_context, facility=""))

    def invalidate_facility_cache(self):
        cache.delete(
            ACTION_CACHE_KEY.format(
                context=self.action_context, facility=self.facility_id
            )
        )

    def invalidate_cache(self):
        if self.facility:
            self.invalidate_facility_cache()
        self.invalidate_instance_cache()

    @classmethod
    def get_instance_actions(cls, context):
        cache_key = ACTION_CACHE_KEY.format(context=context, facility="")
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        actions = list(
            cls.objects.filter(
                action_context=context, facility__isnull=True
            ).values_list("actions", flat=True)
        )
        cache.set(cache_key, actions, 60 * 60 * 24)
        return actions

    @classmethod
    def get_facility_actions(cls, context, facility):
        cache_key = ACTION_CACHE_KEY.format(context=context, facility=facility.id)
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        actions = list(
            cls.objects.filter(action_context=context, facility=facility).values_list(
                "actions", flat=True
            )
        )
        cache.set(cache_key, actions, 60 * 60 * 24)
        return actions

    @classmethod
    def get_actions_for_context(cls, context, facility):
        return cls.get_instance_actions(context) + cls.get_facility_actions(
            context, facility
        )
