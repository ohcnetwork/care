# Generated by Django 4.2.2 on 2023-08-01 19:32

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0005_alter_user_alt_phone_number_alter_user_phone_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="weekly_working_hours",
            field=models.IntegerField(
                default=168,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(168),
                ],
            ),
        ),
    ]
