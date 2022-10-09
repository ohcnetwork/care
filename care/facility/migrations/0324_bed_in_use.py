# Generated by Django 2.2.11 on 2022-07-20 20:47

from django.db import migrations, models


def set_bed_status(apps, schema_editor):
    ConsultationBed = apps.get_model("facility", "ConsultationBed")
    Bed = apps.get_model("facility", "Bed")

    consultation_bed_objs = ConsultationBed.objects.all()
    bed_objs = []

    for consultation_bed in consultation_bed_objs:
        if consultation_bed.end_date is None:
            bed = consultation_bed.bed
            bed.in_use = True
            bed_objs.append(bed)

    Bed.objects.bulk_update(bed_objs, fields=["in_use"])


class Migration(migrations.Migration):

    dependencies = [
        ("facility", "0323_fileupload_archive_reason"),
    ]

    operations = [
        migrations.AddField(
            model_name="bed",
            name="in_use",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(set_bed_status, migrations.RunPython.noop),
    ]
