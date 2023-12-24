from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.db import models

from care.utils.event_utils import CustomJSONEncoder

User = get_user_model()


class EventType(models.Model):
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        null=True,
    )
    name = models.CharField(
        max_length=100, null=False, blank=False, unique=True, db_index=True
    )
    description = models.TextField(null=True, blank=True)
    model = models.CharField(max_length=50, db_index=True)
    fields = ArrayField(models.CharField(max_length=50), default=list)
    created_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def get_descendants(self):
        descendants = list(self.children.all())
        for child in self.children.all():
            descendants.extend(child.get_descendants())
        return descendants

    def save(self, *args, **kwargs):
        if self.description is not None and not self.description.strip():
            self.description = None
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.model} - {self.name}"


class PatientConsultationEvent(models.Model):
    # external_id = use ulid
    consultation = models.ForeignKey(
        "PatientConsultation",
        on_delete=models.PROTECT,
        related_name="events",
    )
    caused_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_date = models.DateTimeField(db_index=True)
    object_model = models.CharField(
        max_length=50, db_index=True, null=False, blank=False
    )
    object_id = models.IntegerField(null=False, blank=False)
    event_type = models.ForeignKey(EventType, null=False, on_delete=models.PROTECT)
    is_latest = models.BooleanField(default=True)
    meta = models.JSONField(default=dict, encoder=CustomJSONEncoder)
    value = models.JSONField(default=dict, encoder=CustomJSONEncoder)

    def __str__(self) -> str:
        return f"{self.consultation_id} - {self.event_type} - {self.created_date}"

    class Meta:
        ordering = ["-created_date"]
        indexes = [models.Index(fields=["consultation", "is_latest"])]
        # constraints = [
        #     models.UniqueConstraint(
        #         fields=["consultation", "event_type", "is_latest"],
        #         condition=models.Q(is_latest=True),
        #         name="unique_consultation_event_type_is_latest",
        #     )
        # ]
