import json
from datetime import datetime

from celery import shared_task
from django.apps import apps
from django.core import serializers
from django.db import models, transaction
from django.db.models import Model
from django.db.models.query import QuerySet
from django.utils.timezone import now

from care.facility.models.events import ChangeType, EventType, PatientConsultationEvent
from care.utils.event_utils import CustomJSONEncoder, model_diff


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
def create_consultation_event_task(
    consultation_id: int,
    object_model: str,
    object_id: int,
    caused_by: int,
    created_date: datetime,
    diff: str = None,
):
    Model = apps.get_model("facility", object_model)

    print(f"Creating Event for {object_model} {object_id}")

    instance = Model.objects.get(id=object_id)

    diff = json.loads(diff) if diff else None
    change_type = ChangeType.UPDATED if diff else ChangeType.CREATED

    data = transform(instance, diff)
    print(data)

    object_fields = set(data.keys())

    with transaction.atomic():
        batch = []
        groups = EventType.objects.filter(
            model=object_model, fields__len__gt=0
        ).values_list("id", "fields")
        print(groups)
        for group_id, group_fields in groups:
            if set(group_fields) & object_fields:
                # PatientConsultationEvent.objects.select_for_update().filter(
                #     consultation_id=consultation_id,
                #     event_type=group_id,
                #     is_latest=True,
                #     created_date__lt=created_date,
                # ).update(is_latest=False)
                value = {}
                for field in group_fields:
                    try:
                        value[field] = data[field]
                    except KeyError:
                        value[field] = getattr(instance, field, None)
                batch.append(
                    PatientConsultationEvent(
                        consultation_id=consultation_id,
                        caused_by_id=caused_by,
                        event_type_id=group_id,
                        is_latest=True,
                        created_date=created_date,
                        object_model=object_model,
                        object_id=object_id,
                        value=value,
                        change_type=change_type,
                        meta={
                            "external_id": str(getattr(instance, "external_id", ""))
                            or None
                        },
                    )
                )

        # print([x.__dict__ for x in batch])

        PatientConsultationEvent.objects.bulk_create(batch)
        return len(batch)


def create_consultation_event(
    consultation_id: int,
    objects: list | QuerySet | Model,
    caused_by: int,
    created_date: datetime = None,
    old: Model = None,
):
    if created_date is None:
        created_date = now()

    if isinstance(objects, (QuerySet, list, tuple)):
        if old is not None:
            raise ValueError("diff is not available when objects is a list or queryset")
        for obj in objects:
            object_model = obj.__class__.__name__
            create_consultation_event_task.apply_async(
                (consultation_id, object_model, obj.id, caused_by, created_date),
                countdown=1,
            )
    else:
        diff = (
            json.dumps(model_diff(old, objects), cls=CustomJSONEncoder) if old else None
        )
        object_model = objects.__class__.__name__
        create_consultation_event_task.apply_async(
            (consultation_id, object_model, objects.id, caused_by, created_date, diff),
            countdown=1,  # delay to avoid accessing db too early
        )
