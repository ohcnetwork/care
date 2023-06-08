# Generated by Django 2.2.11 on 2020-03-28 12:09

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("facility", "0035_auto_20200328_0442"),
    ]

    operations = [
        migrations.AddField(
            model_name="patientconsultation",
            name="created_by",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
