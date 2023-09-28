from django.db import models


class MetaHubSpokes(models.Model):
    """
    Not for production use. For Metabase purposes only.
    Do not build relations to this model.
    """

    state = models.CharField(max_length=255)
    hub = models.CharField(max_length=255, help_text="Hub hospital name")
    spoke = models.CharField(max_length=255, help_text="Spoke hospital name")

    class Meta:
        db_table = "meta_hub_spokes"
