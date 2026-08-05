from django.contrib.postgres.fields import ArrayField
from django.db import models

from care.emr.models import EMRBaseModel
from care.utils.lock import Lock


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
    metadata = models.JSONField(default=None, null=True, blank=True)

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
        if self.parent_id and self.cached_parent_json:
            return self.cached_parent_json
        return {}

    def update_parent_json(self):
        with Lock(f"tag_config_parent_cache:{self.id}"):
            if self.parent_id:
                self.cached_parent_json = {
                    "id": str(self.parent.external_id),
                    "display": self.parent.display,
                    "description": self.parent.description,
                    "category": self.parent.category,
                    "parent": self.parent.cached_parent_json,
                    "level_cache": self.parent.level_cache,
                }
                super().save(update_fields=["cached_parent_json"])

    def update_child_cached_parent_json(self):
        for child in TagConfig.objects.filter(parent=self).select_related("parent"):
            child.update_parent_json()
            child.update_child_cached_parent_json()

    def save(self, *args, **kwargs):
        if not self.id:
            super().save(*args, **kwargs)
            self.set_tag_config_cache()
            self.update_parent_json()
        else:
            super().save(*args, **kwargs)
            self.update_parent_json()
            self.update_child_cached_parent_json()
