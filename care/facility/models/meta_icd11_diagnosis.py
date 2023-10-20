from django.db import models


class MetaICD11Diagnosis(models.Model):
    """
    Not for production use. For Metabase purposes only. Do not build relations to this model.

    Deprecated in favor of ICD11Diagnosis. This table will be removed in the future.
    """

    id = models.CharField(max_length=255, primary_key=True)
    _id = models.IntegerField()
    average_depth = models.IntegerField()
    is_adopted_child = models.BooleanField()
    parent_id = models.CharField(max_length=255, null=True)
    class_kind = models.CharField(max_length=255)
    is_leaf = models.BooleanField()
    label = models.CharField(max_length=255)
    breadth_value = models.DecimalField(max_digits=24, decimal_places=22)
    chapter = models.CharField(max_length=255)
    chapter_short = models.CharField(max_length=255, null=True)
    root_block = models.CharField(max_length=255, null=True)
    root_category = models.CharField(max_length=255, null=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "meta_icd11_diagnosis"

    def __str__(self):
        return self.label
