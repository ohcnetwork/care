
from django.db import models

from care.utils.models.base import BaseModel


class PermissionModel(BaseModel):
    """
    This model represents a permission in the security system.
    A permission allows a certain action to be performed by the user for a given context.
    """
    name = models.CharField(max_length=1024)
    description = models.TextField(default="")
    context = models.CharField(max_length=1024) # We can add choices here as well if needed
