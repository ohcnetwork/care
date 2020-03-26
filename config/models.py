from django.db import models


class CareManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        filters = {"deleted": False}
        if getattr(self.model, "is_active", None):
            filters["is_active"] = True
        return qs.filter(**filters)


class CareBaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    objects = CareManager()

    class Meta:
        abstract = True

    def delete(self):
        self.deleted = True
        self.save()
