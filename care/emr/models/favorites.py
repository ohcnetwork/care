from django.contrib.postgres.fields import ArrayField
from django.db import models

from care.emr.models import EMRBaseModel
from care.facility.models.facility import Facility
from care.users.models import User


class UserResourceFavorites(EMRBaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    favorites = ArrayField(models.IntegerField(), default=list)
    favorite_list = models.CharField(max_length=255)
    resource_type = models.CharField(max_length=255)
    facility = models.ForeignKey(
        Facility, on_delete=models.CASCADE, null=True, blank=True
    )
