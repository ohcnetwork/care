from uuid import uuid4

from django.db import models


class BaseManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(deleted=False)

    def filter(self, *args, **kwargs):
        _id = kwargs.pop("id", "----")
        if _id != "----" and not isinstance(_id, int):
            kwargs["external_id"] = _id
        return super().filter(*args, **kwargs)


class BaseModel(models.Model):
    external_id = models.UUIDField(default=uuid4, unique=True, db_index=True)
    created_date = models.DateTimeField(auto_now_add=True, null=True, blank=True, db_index=True)
    modified_date = models.DateTimeField(auto_now=True, null=True, blank=True, db_index=True)
    deleted = models.BooleanField(default=False, db_index=True)

    objects = BaseManager()

    class Meta:
        abstract = True

    def delete(self, *args):
        self.deleted = True
        self.save()
