from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0351_auto_20230424_1227"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="shiftingrequest",
            name="patient_category",
        ),
    ]
