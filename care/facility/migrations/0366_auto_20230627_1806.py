# Generated by Django 4.2.2 on 2023-06-27 12:36

from django.db import migrations
from django.db.models import F


class Migration(migrations.Migration):
    def fix_expired_discharge_date(apps, schema_editor):
        PatientConsultation = apps.get_model("facility", "PatientConsultation")
        PatientConsultation.objects.filter(
            discharge_reason="EXP", death_datetime__isnull=False
        ).update(discharge_date=F("death_dateime"))

    dependencies = [
        ("facility", "0365_merge_20230626_1834"),
    ]

    operations = [
        migrations.RunPython(
            fix_expired_discharge_date, reverse_code=migrations.RunPython.noop
        )
    ]
