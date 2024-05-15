from datetime import datetime

from django.db import transaction
from django.db.models import Model
from django.db.models.query import QuerySet
from django.utils.timezone import now

from care.facility.models.events import ChangeType, EventType, PatientConsultationEvent
from care.utils.event_utils import get_changed_fields, serialize_field


def transform(
    object_instance: Model,
    old_instance: Model,
    fields_to_store: set | None = None,
) -> dict:
    fields = set()
    if old_instance:
        changed_fields = get_changed_fields(old_instance, object_instance)
        fields = {
            field
            for field in object_instance._meta.fields
            if field.name in changed_fields
        }
    else:
        fields = set(object_instance._meta.fields)

    if fields_to_store:
        fields &= fields_to_store

    return {field.name: serialize_field(object_instance, field) for field in fields}


def create_consultation_event_entry(
    consultation_id: int,
    object_instance: Model,
    caused_by: int,
    created_date: datetime,
    old_instance: Model = None,
    fields_to_store: set | None = None,
):
    change_type = ChangeType.UPDATED if old_instance else ChangeType.CREATED

    data = transform(object_instance, old_instance, fields_to_store)

    fields_to_store = fields_to_store or set(data.keys())

    batch = []
    groups = EventType.objects.filter(
        model=object_instance.__class__.__name__, fields__len__gt=0
    ).values_list("id", "fields")
    for group_id, group_fields in groups:
        if set(group_fields) & fields_to_store:
            value = {}
            for field in group_fields:
                try:
                    value[field] = data[field]
                except KeyError:
                    value[field] = getattr(object_instance, field, None)
            # if all values in the group are Falsy, skip creating the event for this group
            if all(not v for v in value.values()):
                continue
            PatientConsultationEvent.objects.select_for_update().filter(
                consultation_id=consultation_id,
                event_type=group_id,
                is_latest=True,
                object_model=object_instance.__class__.__name__,
                object_id=object_instance.id,
                created_date__lt=created_date,
            ).update(is_latest=False)
            batch.append(
                PatientConsultationEvent(
                    consultation_id=consultation_id,
                    caused_by_id=caused_by,
                    event_type_id=group_id,
                    is_latest=True,
                    created_date=created_date,
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
    created_date: datetime = None,
    old: Model | None = None,
    fields_to_store: list | set | None = None,
):
    if created_date is None:
        created_date = now()

    with transaction.atomic():
        if isinstance(objects, (QuerySet, list, tuple)):
            if old is not None:
                raise ValueError(
                    "diff is not available when objects is a list or queryset"
                )
            for obj in objects:
                create_consultation_event_entry(
                    consultation_id,
                    obj,
                    caused_by,
                    created_date,
                    fields_to_store=set(fields_to_store) if fields_to_store else None,
                )
        else:
            create_consultation_event_entry(
                consultation_id,
                objects,
                caused_by,
                created_date,
                old,
                fields_to_store=set(fields_to_store) if fields_to_store else None,
            )
