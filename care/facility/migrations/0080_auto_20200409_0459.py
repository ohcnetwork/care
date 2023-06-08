# Generated by Django 2.2.11 on 2020-04-08 23:29

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0079_auto_20200409_0451"),
    ]

    operations = [
        migrations.AddField(
            model_name="patientconsultation",
            name="created_date",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name="patientconsultation",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="patientconsultation",
            name="modified_date",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]
