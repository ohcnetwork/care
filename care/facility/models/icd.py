from django.db import models


class ICDDisease(models.Model):
    id = models.CharField(primary_key=True, unique=True,
                          max_length=1024, blank=False, null=False)
    label = models.CharField(max_length=1024, blank=False, null=False)
    is_leaf = models.BooleanField(default=False, null=False, blank=False)
    class_kind = models.CharField(max_length=1024, blank=False, null=False)
    is_adopted_child = models.BooleanField(default=False, null=False, blank=False)
    average_depth = models.FloatField(null=False, blank=False)
    parent_id = models.CharField(max_length=1024, blank=False, null=True)
