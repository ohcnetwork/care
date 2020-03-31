from django.db import migrations


def delete_duplicates(apps, *args):
    Disease = apps.get_model("facility", "Disease")

    # .order_by("-id") so that latest record is retained
    records = Disease.objects.all().order_by("-id").values("id", "patient", "disease")
    checked = []
    to_be_deleted = set()
    for record in records:
        _id = record.pop("id")
        if record in checked:
            to_be_deleted.add(_id)
        else:
            checked.append(record)
    Disease.objects.filter(id__in=to_be_deleted).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("facility", "0052_remove_patientconsultation_created_by"),
    ]

    operations = [
        migrations.RunPython(delete_duplicates),
    ]
