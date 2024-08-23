# Generated by Django 4.2.8 on 2024-05-17 04:55

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0436_remove_dailyround_temperature_measured_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dailyround",
            name="rounds_type",
            field=models.IntegerField(
                choices=[
                    (0, "NORMAL"),
                    (50, "DOCTORS_LOG"),
                    (100, "VENTILATOR"),
                    (200, "ICU"),
                    (300, "AUTOMATED"),
                    (400, "TELEMEDICINE"),
                ],
                default=0,
            ),
        ),
    ]
