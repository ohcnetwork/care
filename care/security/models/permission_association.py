from django.db import models

from care.security.models.role import RoleModel
from care.users.models import User
from care.utils.models.base import BaseModel


class RoleAssociation(BaseModel):
    """
    This model connects roles to users via contexts
    Expiry can be used to expire the role allocation after a certain period
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False)
    context = models.CharField(max_length=1024)
    context_id = models.BigIntegerField()  # Store integer id of the context here
    role = models.ForeignKey(
        RoleModel, on_delete=models.CASCADE, null=False, blank=False
    )
    expiry = models.DateTimeField(null=True, blank=True)

    # TODO : Index user, context and context_id
