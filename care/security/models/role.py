from django.db import models
from django.db.models import UniqueConstraint

from care.security.models.permission import PermissionModel
from care.utils.models.base import BaseModel


class RoleModel(BaseModel):
    """
    This model represents a role in the security system.
    A role comprises multiple permissions on the same type.
    A role can only be made for a single context. eg, A role can be FacilityAdmin with Facility related permission items
    Another role is to be created for other contexts, eg. Asset Admin should only contain Asset related permission items
    Roles can be created on the fly, System roles cannot be deleted, but user created roles can be deleted by users
    with the permission to delete roles
    """

    name = models.CharField(max_length=1024)
    description = models.TextField(default="")
    context = models.CharField(
        max_length=1024
    )  # We can add choices here as well if needed
    is_system = models.BooleanField(
        default=False
    )  # Denotes if role was created on the fly
    temp_deleted = models.BooleanField(default=False)

    class Meta:
        constraints = [
            UniqueConstraint(name="unique_order", fields=["name", "context"])
        ]


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
