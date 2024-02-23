from django.db import migrations, models


def clean_duplicates(apps, schema_editor):
    AvailabilityRecord = apps.get_model("facility", "AvailabilityRecord")

    duplicates = (
        AvailabilityRecord.objects.values("object_external_id", "timestamp")
        .annotate(count=models.Count("id"))
        .filter(count__gt=1)
    )

    ids_to_delete = []
    for duplicate in duplicates:
        record_ids = list(
            AvailabilityRecord.objects.filter(
                object_external_id=duplicate["object_external_id"],
                timestamp=duplicate["timestamp"],
            ).values_list("id", flat=True)
        )

        ids_to_delete.extend(record_ids[1:])

    if ids_to_delete:
        AvailabilityRecord.objects.filter(id__in=set(ids_to_delete)).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0411_merge_20240212_1429"),
    ]

    operations = [
        migrations.RunPython(clean_duplicates, reverse_code=migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="availabilityrecord",
            constraint=models.UniqueConstraint(
                fields=("object_external_id", "timestamp"),
                name="object_external_id_timestamp_unique",
            ),
        ),
    ]
