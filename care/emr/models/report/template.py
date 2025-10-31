from django.db import models

from care.emr.models import SlugBaseModel


class Template(SlugBaseModel):
    facility = models.ForeignKey(
        "facility.Facility",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    slug = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    template_data = models.TextField()
    template_type = models.CharField(max_length=255)
    format = models.CharField(max_length=255)
    context_config = models.JSONField(default=dict, blank=True)
