from django.db import migrations, models

import care.parxio_core.compat


class Migration(migrations.Migration):
    dependencies = [
        ("parxio_core", "0001_initial"),
        ("facility", "0484_remove_facility_discount_codes_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="facility",
            name="tenant",
            field=care.parxio_core.compat.TenantForeignKey(
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name="facilities",
                to="parxio_core.tenant",
            ),
        ),
    ]
