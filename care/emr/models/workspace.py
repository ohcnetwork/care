from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

from care.emr.models import EMRBaseModel
from care.emr.models.organization import FacilityOrganization, Organization
from care.users.models import User

WORKSPACE_USER_DEFAULT_CACHE_KEY = "workspace_user_default:{user_id}"


class Workspace(EMRBaseModel):
    facility = models.ForeignKey(
        "facility.Facility", on_delete=models.CASCADE, null=True, blank=True
    )
    facility_organization = models.ForeignKey(
        "emr.FacilityOrganization", on_delete=models.CASCADE, null=True, blank=True
    )
    auth_context = models.CharField(max_length=255, default="instance")
    name = models.CharField(max_length=255)
    description = models.TextField(default="")
    template = models.JSONField(default=dict)
    internal_organization_cache = ArrayField(models.IntegerField(), default=list)
    organization_cache = ArrayField(models.IntegerField(), default=list)

    def sync_facility_org_cache(self):
        from care.emr.resources.workspace.spec import WorkspaceAuthContext

        if self.auth_context == WorkspaceAuthContext.facility_organization:
            organization_ids = [
                *self.facility_organization.parent_cache,
                self.facility_organization.id,
            ]
        elif self.auth_context == WorkspaceAuthContext.facility:
            workspace_organization_objects = (
                WorkspaceFacilityOrganization.objects.filter(
                    workspace=self
                ).select_related("organization")
            )
            organization_ids = []
            for workspace_organization_object in workspace_organization_objects:
                organization_ids.extend(
                    workspace_organization_object.organization.parent_cache
                )
                organization_ids.append(workspace_organization_object.organization.id)
        else:
            return
        self.internal_organization_cache = list(set(organization_ids))
        self.save(update_fields=["internal_organization_cache"])

    def sync_organization_cache(self):
        from care.emr.resources.workspace.spec import WorkspaceAuthContext

        organization_ids = []
        if self.auth_context == WorkspaceAuthContext.instance:
            workspace_organization_objects = WorkspaceOrganization.objects.filter(
                workspace=self
            ).select_related("organization")
            for workspace_organization_object in workspace_organization_objects:
                organization_ids.extend(
                    workspace_organization_object.organization.parent_cache
                )
                organization_ids.append(workspace_organization_object.organization.id)
            self.organization_cache = list(set(organization_ids))
            self.save(update_fields=["organization_cache"])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.invalidate_user_default_cache()

    def invalidate_user_default_cache(self):
        user_ids = WorkSpaceUserDefault.objects.filter(
            workspace_id=self.id
        ).values_list("user_id", flat=True)
        cache.delete_many(
            [WorkSpaceUserDefault.get_cache_key(user_id) for user_id in user_ids]
        )


class WorkspaceFacilityOrganization(EMRBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    organization = models.ForeignKey(FacilityOrganization, on_delete=models.CASCADE)


class WorkspaceOrganization(EMRBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)


class WorkSpaceUserDefault(EMRBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    attribute = models.CharField(max_length=255, null=True, blank=True)
    value = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "user", "attribute", "value"],
                condition=models.Q(deleted=False),
                nulls_distinct=False,
                name="unique_workspace_user_attribute_value",
            )
        ]

    @classmethod
    def get_cache_key(cls, user_id):
        return WORKSPACE_USER_DEFAULT_CACHE_KEY.format(user_id=user_id)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.invalidate_cache()

    def invalidate_cache(self):
        if self.user_id:
            cache.delete(self.get_cache_key(self.user_id))


@receiver(post_delete, sender=WorkSpaceUserDefault)
def invalidate_workspace_user_default_cache(sender, instance, **kwargs):
    instance.invalidate_cache()
