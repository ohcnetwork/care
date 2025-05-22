from django.core.cache import cache
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from care.security.models.permission import PermissionModel
from care.utils.models.base import BaseModel

ROLE_PERMISSIONS_CACHE_KEY = "role_permissions:{}"
ROLE_PERMISSION_SK_CACHE_KEY = "role_permissions_cache:{}"
CACHE_TIMEOUT = 60 * 60 * 24 * 7  # 7 days


class RoleModel(BaseModel):
    """
    This model represents a role in the security system.
    A role comprises multiple permissions on the same type.
    Roles can be created on the fly, System roles cannot be deleted, but user created roles can be deleted by users
    with the permission to delete roles
    """

    name = models.CharField(max_length=1024)
    description = models.TextField(default="")
    is_system = models.BooleanField(
        default=False
    )  # Denotes if role was created by the system or a user
    temp_deleted = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=models.Q(deleted=False),
                name="unique_name_if_not_deleted",
            )
        ]

    def get_permission_sk_for_role(self):
        """
        Create a cache key for the role permissions
        """
        cache_key = ROLE_PERMISSION_SK_CACHE_KEY.format(self.id)

        cached_permissions = cache.get(cache_key)
        if cached_permissions is not None:
            return cached_permissions

        permissions = list(
            PermissionModel.objects.filter(
                rolepermission__role=self, rolepermission__temp_deleted=False
            ).values_list("slug", flat=True)
        )

        cache.set(cache_key, permissions, CACHE_TIMEOUT)

        return permissions

    def get_permissions_for_role(self):
        """
        Returns all permissions associated with this role.
        Uses Redis cache to improve performance.
        """
        cache_key = ROLE_PERMISSIONS_CACHE_KEY.format(self.id)

        # Try to get permissions from cache
        cached_permissions = cache.get(cache_key)
        if cached_permissions is not None:
            return cached_permissions

        # If not in cache, fetch from database
        permissions = [
            {
                "name": x.name,
                "slug": x.slug,
                "context": x.context,
                "description": x.description,
            }
            for x in PermissionModel.objects.filter(
                rolepermission__role=self, rolepermission__temp_deleted=False
            )
        ]

        # Store in cache
        cache.set(cache_key, permissions, CACHE_TIMEOUT)

        return permissions


class RolePermission(BaseModel):
    """
    Connects a role to a list of permissions
    """

    role = models.ForeignKey(
        RoleModel, on_delete=models.CASCADE, null=False, blank=False
    )
    permission = models.ForeignKey(
        PermissionModel, on_delete=models.CASCADE, null=False, blank=False
    )
    temp_deleted = models.BooleanField(default=False)


# Signal handlers to invalidate cache when permissions change
@receiver([post_save, post_delete], sender=RolePermission)
def invalidate_role_permissions_cache(sender, instance, **kwargs):
    """
    Invalidate the cache when a RolePermission is created, updated, or deleted
    """
    cache_key = ROLE_PERMISSIONS_CACHE_KEY.format(instance.role_id)
    cache.delete(cache_key)
    cache_key = ROLE_PERMISSION_SK_CACHE_KEY.format(instance.role_id)
    cache.delete(cache_key)
