from django.db import models


class ICD11ClassKind(models.TextChoices):
    CHAPTER = "chapter"
    BLOCK = "block"
    CATEGORY = "category"


class ICD11Diagnosis(models.Model):
    """
    Use ICDDiseases for in-memory search.
    """

    id = models.BigIntegerField(primary_key=True)
    icd11_id = models.CharField(max_length=255, unique=True)
    label = models.CharField(max_length=255)
    class_kind = models.CharField(max_length=255, choices=ICD11ClassKind.choices)
    is_leaf = models.BooleanField()
    parent = models.ForeignKey("self", on_delete=models.DO_NOTHING, null=True)
    average_depth = models.IntegerField()
    is_adopted_child = models.BooleanField()
    breadth_value = models.DecimalField(max_digits=24, decimal_places=22)

    # Meta fields
    meta_hidden = models.BooleanField(default=False)
    meta_chapter = models.CharField(max_length=255)
    meta_chapter_short = models.CharField(max_length=255, null=True)
    meta_root_block = models.CharField(max_length=255, null=True)
    meta_root_category = models.CharField(max_length=255, null=True)

    def __str__(self) -> str:
        return self.label
