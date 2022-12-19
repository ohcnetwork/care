# from django.db import models

# Create your models here.

from django.db import models

from care.utils.models.base import BaseModel


class AbhaNumber(BaseModel):
    abha_number = models.CharField(max_length=50)
    email = models.CharField(max_length=50)
    first_name = models.CharField(max_length=50)
    health_id = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50)
    password = models.CharField(max_length=50)
    profile_photo = models.CharField(max_length=50)
    txn_id = models.CharField(max_length=50)

    access_token = models.CharField(max_length=50)
    refresh_token = models.CharField(max_length=50)

    def __str__(self):
        return self.abha_number
