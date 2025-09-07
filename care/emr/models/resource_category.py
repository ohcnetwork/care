from datetime import datetime, timedelta

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone

from care.emr.models.base import EMRBaseModel


class ResourceCategory(EMRBaseModel):
    facility = models.ForeignKey(
        "facility.Facility",
        on_delete=models.PROTECT,
    )
    resource_type = models.CharField(max_length=255)
    resource_sub_type = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    slug = models.CharField(max_length=25)
    description = models.TextField(null=True, blank=True)
    parent = models.ForeignKey(
        "emr.ResourceCategory",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    is_child = models.BooleanField(default=False)
    cached_parent_json = models.JSONField(default=dict)
    parent_cache = ArrayField(models.IntegerField(), default=list)
    level_cache = models.IntegerField(default=0)
    root_org = models.ForeignKey(
        "emr.ResourceCategory",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="root",
    )
    has_children = models.BooleanField(default=False)

    cache_expiry_days = 15

    class Meta:
        indexes = [
            models.Index(fields=["slug", "facility"]),
        ]

    def set_organization_cache(self):
        if self.parent:
            self.parent_cache = [*self.parent.parent_cache, self.parent.id]
            self.level_cache = self.parent.level_cache + 1
            if self.parent.root_org is None:
                self.root_org = self.parent
            else:
                self.root_org = self.parent.root_org
            if not self.parent.has_children:
                self.parent.has_children = True
                self.parent.save(update_fields=["has_children"])
        super().save()

    def get_parent_json(self):
        if self.parent_id:
            if self.cached_parent_json and timezone.now() < datetime.fromisoformat(
                self.cached_parent_json["cache_expiry"]
            ):
                return self.cached_parent_json
            self.parent.get_parent_json()
            self.cached_parent_json = {
                "id": str(self.parent.external_id),
                "slug": self.parent.slug,
                "title": self.parent.title,
                "description": self.parent.description,
                "parent": self.parent.cached_parent_json,
                "cache_expiry": str(
                    timezone.now() + timedelta(days=self.cache_expiry_days)
                ),
            }
            self.save(update_fields=["cached_parent_json"])
            return self.cached_parent_json
        return {}

    def save(self, *args, **kwargs):
        if not self.id:
            super().save(*args, **kwargs)
            self.set_organization_cache()
        else:
            super().save(*args, **kwargs)
