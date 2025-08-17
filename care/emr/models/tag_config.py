from datetime import datetime, timedelta

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone

from care.emr.models import EMRBaseModel


class TagConfig(EMRBaseModel):
    """
    Represents a config for a tag
    """

    facility = models.ForeignKey(
        "facility.Facility",
        on_delete=models.PROTECT,
        default=None,
        null=True,
        blank=True,
    )
    facility_organization = models.ForeignKey(
        "emr.FacilityOrganization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    organization = models.ForeignKey(
        "emr.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=255)
    slug = models.CharField(max_length=255)
    display = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=255)
    priority = models.IntegerField(default=100)
    level_cache = models.IntegerField(default=0)
    parent_cache = ArrayField(models.IntegerField(), default=list)
    cached_parent_json = models.JSONField(default=dict)
    parent = models.ForeignKey(
        "self", related_name="children", on_delete=models.CASCADE, null=True, blank=True
    )
    has_children = models.BooleanField(default=False)
    root_tag_config = models.ForeignKey(
        "self",
        related_name="root",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    resource = models.CharField(max_length=255)
    cache_expiry_days = 15

    def set_tag_config_cache(self):
        if self.parent:
            self.parent_cache = [*self.parent.parent_cache, self.parent.id]
            self.level_cache = self.parent.level_cache + 1
            if self.parent.root_tag_config is None:
                self.root_tag_config = self.parent
            else:
                self.root_tag_config = self.parent.root_tag_config
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
                "display": self.parent.display,
                "description": self.parent.description,
                "category": self.parent.category,
                "parent": self.parent.cached_parent_json,
                "level_cache": self.parent.level_cache,
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
            self.set_tag_config_cache()
        else:
            super().save(*args, **kwargs)
