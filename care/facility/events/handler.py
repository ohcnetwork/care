from contextlib import suppress
from datetime import datetime

from django.core.exceptions import FieldDoesNotExist
from django.db import transaction
from django.db.models import Model
from django.db.models.query import QuerySet
from django.utils.timezone import now

from care.facility.models.events import ChangeType, EventType, PatientConsultationEvent
from care.utils.event_utils import get_changed_fields, serialize_field


def create_consultation_event_entry(
    consultation_id: int,
    object_instance: Model,
    caused_by: int,
    created_date: datetime,
    taken_at: datetime,
    old_instance: Model | None = None,
    fields_to_store: set[str] | None = None,
):
    change_type = ChangeType.UPDATED if old_instance else ChangeType.CREATED

    fields: set[str] = (
        get_changed_fields(old_instance, object_instance)
        if old_instance
        else {field.name for field in object_instance._meta.fields}  # noqa: SLF001
    )

    fields_to_store = fields_to_store & fields if fields_to_store else fields

    batch = []
    groups = EventType.objects.filter(
        model=object_instance.__class__.__name__, fields__len__gt=0, is_active=True
    ).values_list("id", "fields")
    for group_id, group_fields in groups:
        if fields_to_store & {field.split("__", 1)[0] for field in group_fields}:
            value = {}
            for field in group_fields:
                with suppress(FieldDoesNotExist):
                    value[field] = serialize_field(object_instance, field)

            if all(not v for v in value.values()):
                continue

            PatientConsultationEvent.objects.select_for_update().filter(
                consultation_id=consultation_id,
                event_type=group_id,
                is_latest=True,
                object_model=object_instance.__class__.__name__,
                object_id=object_instance.id,
                taken_at__lt=taken_at,
            ).update(is_latest=False)
            batch.append(
                PatientConsultationEvent(
                    consultation_id=consultation_id,
                    caused_by_id=caused_by,
                    event_type_id=group_id,
                    is_latest=True,
                    created_date=created_date,
                    taken_at=taken_at,
                    object_model=object_instance.__class__.__name__,
                    object_id=object_instance.id,
                    value=value,
                    change_type=change_type,
                    meta={
                        "external_id": str(getattr(object_instance, "external_id", ""))
                        or None
                    },
                )
            )

    PatientConsultationEvent.objects.bulk_create(batch)
    return len(batch)


def create_consultation_events(
    consultation_id: int,
    objects: list | QuerySet | Model,
    caused_by: int,
    created_date: datetime | None = None,
    taken_at: datetime | None = None,
    old: Model | None = None,
    fields_to_store: list[str] | set[str] | None = None,
):
    if created_date is None:
        created_date = now()

    if taken_at is None:
        taken_at = created_date

    with transaction.atomic():
        if isinstance(objects, QuerySet | list | tuple):
            if old is not None:
                msg = "diff is not available when objects is a list or queryset"
                raise ValueError(msg)
            for obj in objects:
                create_consultation_event_entry(
                    consultation_id,
                    obj,
                    caused_by,
                    created_date,
                    taken_at,
                    fields_to_store=set(fields_to_store) if fields_to_store else None,
                )
        else:
            create_consultation_event_entry(
                consultation_id,
                objects,
                caused_by,
                created_date,
                taken_at,
                old,
                fields_to_store=set(fields_to_store) if fields_to_store else None,
            )
