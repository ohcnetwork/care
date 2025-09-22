import uuid

from django.db import models

from care.utils.models.base import BaseModel


class EMRBaseModel(BaseModel):
    history = models.JSONField(default=dict)
    meta = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
        related_name="%(app_label)s_%(class)s_created_by",
    )
    updated_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
        related_name="%(app_label)s_%(class)s_updated_by",
    )

    class Meta:
        abstract = True


class SlugBaseModel(EMRBaseModel):
    FACILITY_SCOPED = True

    class Meta:
        abstract = True

    @classmethod
    def calculate_slug_from_facility(cls, facility_external_id, slug):
        return f"f-{facility_external_id}-{slug}"

    @classmethod
    def calculate_slug_from_instance(cls, slug):
        return f"i-{slug}"

    def calculate_slug(self):
        if self.FACILITY_SCOPED and self.facility:
            return f"f-{self.facility.external_id}-{self.slug}"
        return f"i-{self.slug}"

    def parse_slug(self, slug):
        if len(slug) <= 2:  # noqa PLR2004
            raise ValueError("Invalid slug")
        if slug.startswith("f-") and self.FACILITY_SCOPED:
            # Facility Scoped slug
            facility_id = slug[2:38]
            uuid.UUID(facility_id)  # Validate UUID
            slug_value = slug[39:]
            return {"facility": facility_id, "slug_value": slug_value}
        if slug.startswith("i-"):
            # instance scoped slug
            slug_value = slug[2:]
            return {"slug_value": slug_value}
        raise ValueError("Invalid slug")
