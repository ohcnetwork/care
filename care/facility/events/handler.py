import json
from datetime import datetime

from celery import shared_task
from django.apps import apps
from django.db import transaction
from django.db.models import Model
from django.db.models.query import QuerySet
from django.utils.timezone import now

from care.facility.models.events import EventType, PatientConsultationEvent
from care.utils.event_utils import CustomJSONEncoder, model_diff


def transform(obj, diff):
    # todo transform data, eg. fetching the fields from the models, joins, etc.
    if diff:
        return diff
    data = {
        field.name: getattr(obj, field.name)
        for field in obj._meta.fields
        # if not is_null(getattr(obj, field.name))
    }
    return data


@shared_task
def create_consultation_event_task(
    consultation_id: int,
    object_class: str,
    object_id: int,
    caused_by: int,
    created_date: datetime,
    diff: str = None,
):
    Model = apps.get_model("facility", object_class)

    print(f"Creating Event for {object_class} {object_id}")

    instance = Model.objects.get(id=object_id)

    diff = json.loads(diff) if diff else None

    data = transform(instance, diff)

    object_fields = set(data.keys())

    with transaction.atomic():
        batch = []
        groups = EventType.objects.filter(
            object_class=object_class, fields__len__gt=0
        ).values_list("id", "fields")
        for group_id, group_fields in groups:
            if group_fields & object_fields:
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
                        event_type=group_id,
                        is_latest=True,
                        created_date=created_date,
                        object_class=object_class,
                        object_id=object_id,
                        value=value,
                    )
                )

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
            object_class = obj.__class__.__name__
            create_consultation_event_task.apply_async(
                (consultation_id, object_class, obj.id, caused_by, created_date),
                countdown=1,
            )
    else:
        diff = (
            json.dumps(model_diff(old, objects), cls=CustomJSONEncoder) if old else None
        )
        object_class = objects.__class__.__name__
        create_consultation_event_task.apply_async(
            (consultation_id, object_class, objects.id, caused_by, created_date, diff),
            countdown=1,  # delay to avoid accessing db too early
        )
