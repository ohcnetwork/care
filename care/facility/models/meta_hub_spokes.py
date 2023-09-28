from django.db import models


class MetaHubSpokes(models.Model):
    state = models.CharField(max_length=255)
    hub = models.CharField(max_length=255, help_text="Hub hospital name")
    spoke = models.CharField(max_length=255, help_text="Spoke hospital name")

    class Meta:
        db_table = "meta_hub_spokes"
