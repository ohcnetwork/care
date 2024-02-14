from datetime import datetime

from celery import shared_task
from django.core import serializers
from django.db import models, transaction
from django.db.models import Model
from django.db.models.query import QuerySet
from django.utils.timezone import now

from care.facility.models.events import ChangeType, EventType, PatientConsultationEvent
from care.utils.event_utils import model_diff


def transform(obj, diff):
    # todo transform data, eg. fetching the fields from the models, joins, etc.
    if diff:
        return diff
    # data = {
    #     field.name: getattr(obj, field.name)
    #     for field in obj._meta.fields
    #     # if not is_null(getattr(obj, field.name))
    # }
    data = {}
    for field in obj._meta.fields:
        value = getattr(obj, field.name)
        if isinstance(value, models.Model):
            data[field.name] = serializers.serialize("python", [value])[0]["fields"]
        else:
            data[field.name] = value
    return data


@shared_task
def create_consultation_event_entry(
    consultation_id: int,
    object_instance: Model,
    caused_by: int,
    created_date: datetime,
    diff: dict | None = None,
):
    change_type = ChangeType.UPDATED if diff else ChangeType.CREATED

    data = transform(object_instance, diff)

    changed_fields = set(data.keys())

    batch = []
    groups = EventType.objects.filter(
        model=object_instance.__class__.__name__, fields__len__gt=0
    ).values_list("id", "fields")
    for group_id, group_fields in groups:
        if set(group_fields) & changed_fields:
            PatientConsultationEvent.objects.select_for_update().filter(
                consultation_id=consultation_id,
                event_type=group_id,
                is_latest=True,
                object_model=object_instance.__class__.__name__,
                object_id=object_instance.id,
                created_date__lt=created_date,
            ).update(is_latest=False)
            value = {}
            for field in group_fields:
                try:
                    value[field] = data[field]
                except KeyError:
                    value[field] = getattr(object_instance, field, None)
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
    old: Model = None,
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
                    consultation_id, obj, caused_by, created_date
                )
        else:
            diff = model_diff(old, objects) if old else None
            create_consultation_event_entry(
                consultation_id, objects, caused_by, created_date, diff
            )
