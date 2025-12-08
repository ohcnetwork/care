from django.db import models

from care.emr.models.base import SlugBaseModel


class ObservationDefinition(SlugBaseModel):
    facility = models.ForeignKey(
        "facility.Facility",
        on_delete=models.PROTECT,
        default=None,
        null=True,
        blank=True,
    )
    version = models.IntegerField(default=1)
    slug = models.CharField(max_length=255)
    title = models.CharField(max_length=1024)
    status = models.CharField(max_length=255)
    description = models.TextField()
    derived_from_uri = models.TextField()
    category = models.CharField(max_length=255, null=True, blank=True)
    code = models.JSONField()
    permitted_data_type = models.CharField(max_length=100)
    body_site = models.JSONField(null=True, blank=True)
    method = models.JSONField(null=True, blank=True)
    permitted_unit = models.JSONField(null=True, blank=True)
    component = models.JSONField(null=True, blank=True)
    qualified_ranges = models.JSONField(default=list, null=True, blank=True)
