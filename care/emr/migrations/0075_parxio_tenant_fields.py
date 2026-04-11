from django.db import migrations, models

import care.parxio_core.compat


class Migration(migrations.Migration):
    dependencies = [
        ("parxio_core", "0001_initial"),
        ("emr", "0074_facilitymonetoryconfig"),
    ]

    operations = [
        migrations.AddField(
            model_name="patient",
            name="tenant",
            field=care.parxio_core.compat.TenantForeignKey(
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name="patients",
                to="parxio_core.tenant",
            ),
        ),
        migrations.AddField(
            model_name="encounter",
            name="tenant",
            field=care.parxio_core.compat.TenantForeignKey(
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name="encounters",
                to="parxio_core.tenant",
            ),
        ),
        migrations.AddField(
            model_name="medicationrequestprescription",
            name="tenant",
            field=care.parxio_core.compat.TenantForeignKey(
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name="medication_request_prescriptions",
                to="parxio_core.tenant",
            ),
        ),
    ]
