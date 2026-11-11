from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("emr", "0103_procedure"),
    ]

    operations = [
        migrations.AddField(
            model_name="schedule",
            name="encounter_type",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
