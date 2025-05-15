from uuid import uuid4

from django.db import models


class BaseManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(deleted=False)


class BaseModel(models.Model):
    external_id = models.UUIDField(default=uuid4, unique=True, db_index=True)
    created_date = models.DateTimeField(
        auto_now_add=True, null=True, blank=True, db_index=True
    )
    modified_date = models.DateTimeField(
        auto_now=True, null=True, blank=True, db_index=True
    )
    deleted = models.BooleanField(default=False, db_index=True)

    objects = BaseManager()

    class Meta:
        abstract = True

    def delete(self, *args):
        self.deleted = True
        self.save(update_fields=["deleted"])
