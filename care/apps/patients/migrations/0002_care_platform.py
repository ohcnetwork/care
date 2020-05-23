# Generated by Django 2.2.11 on 2020-05-23 07:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("facility", "0003_care_platform"),
        ("patients", "0001_care_platform"),
    ]

    operations = [
        migrations.AddField(
            model_name="patientsampletest",
            name="testing_lab",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="testing_lab",
                to="facility.TestingLab",
            ),
        ),
    ]
