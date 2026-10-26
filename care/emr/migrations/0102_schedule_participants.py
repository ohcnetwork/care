import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("emr", "0101_facilitylocation_child_flags"),
    ]

    operations = [
        migrations.AddField(
            model_name="schedule",
            name="care_team",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="schedule",
            name="organizations",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.IntegerField(), default=list
            ),
        ),
    ]
