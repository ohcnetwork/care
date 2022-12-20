# from django.db import models

# Create your models here.

from django.db import models

from care.utils.models.base import BaseModel


class AbhaNumber(BaseModel):
    abha_number = models.TextField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    first_name = models.TextField(null=True, blank=True)
    health_id = models.TextField(null=True, blank=True)
    last_name = models.TextField(null=True, blank=True)
    middle_name = models.TextField(null=True, blank=True)
    profile_photo = models.TextField(null=True, blank=True)  # What is profile photo? how is it stored as?
    txn_id = models.TextField(null=True, blank=True)  # 50?

    access_token = models.TextField(null=True, blank=True)  # 50 seems a bit too low for access tokens
    refresh_token = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.abha_number
