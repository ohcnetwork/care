from datetime import datetime, timedelta

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone

from care.emr.models import EMRBaseModel


class OrganizationCommonBase(EMRBaseModel):
    active = models.BooleanField(default=True)
    root_org = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="root", null=True, blank=True
    )
    org_type = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    has_children = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
    system_generated = models.BooleanField(default=False)
    parent = models.ForeignKey(
        "self", related_name="children", on_delete=models.CASCADE, null=True, blank=True
    )
    level_cache = models.IntegerField(default=0)
    parent_cache = ArrayField(models.IntegerField(), default=list)
    metadata = models.JSONField(default=dict)
    cached_parent_json = models.JSONField(default=dict)
    cache_expiry_days = 15
    # Storing parent data within the organization to save joins each time

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
                "name": self.parent.name,
                "description": self.parent.description,
                "org_type": self.parent.org_type,
                "metadata": self.parent.metadata,
                "parent": self.parent.cached_parent_json,
                "level_cache": self.parent.level_cache,
                "cache_expiry": str(
                    timezone.now() + timedelta(days=self.cache_expiry_days)
                ),
            }
            self.save(update_fields=["cached_parent_json"])
            return self.cached_parent_json
        return {}

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.id:
            super().save(*args, **kwargs)
            self.set_organization_cache()
        else:
            super().save(*args, **kwargs)

    @classmethod
    def validate_uniqueness(cls, queryset, pydantic_instance, model_instance):
        if model_instance:
            name = model_instance.name
            level_cache = model_instance.level_cache
            root_org = model_instance.root_org
            queryset = queryset.exclude(id=model_instance.id)
        else:
            name = pydantic_instance.name
            if pydantic_instance.parent:
                parent = cls.objects.get(external_id=pydantic_instance.parent)
                level_cache = parent.level_cache + 1
                root_org = parent.root_org
                if not root_org:
                    root_org = parent
            else:
                level_cache = 0
                root_org = None
        if root_org:
            queryset = queryset.filter(root_org=root_org)
        else:
            queryset = queryset.filter(root_org__isnull=True)
        queryset = queryset.filter(level_cache=level_cache, name=name)
        return queryset.exists()


class FacilityOrganization(OrganizationCommonBase):
    facility = models.ForeignKey("facility.Facility", on_delete=models.CASCADE)


class Organization(OrganizationCommonBase):
    pass


class OrganizationUser(EMRBaseModel):
    """
    This model represents how an organization can access an entity,
    ex, Organization can access Patients through role X,
    This does not mean that the organization has access to all patients,
    only the ones assigned to them. when assigning the organization the user has an
    option to override the role to give or take permissions.
    """

    organization = models.ForeignKey("Organization", on_delete=models.CASCADE)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    role = models.ForeignKey("security.RoleModel", on_delete=models.CASCADE)


class FacilityOrganizationUser(EMRBaseModel):
    """
    Same as OrganizationContextRole but for facility scoped organizations
    """

    organization = models.ForeignKey("FacilityOrganization", on_delete=models.CASCADE)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    role = models.ForeignKey("security.RoleModel", on_delete=models.CASCADE)
