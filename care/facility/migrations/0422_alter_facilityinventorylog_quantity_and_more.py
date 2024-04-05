# Generated by Django 4.2.10 on 2024-03-22 11:21

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0421_merge_20240318_1434"),
    ]

    operations = [
        migrations.AlterField(
            model_name="facilityinventorylog",
            name="quantity",
            field=models.FloatField(
                default=0, validators=[django.core.validators.MinValueValidator(0.0)]
            ),
        ),
        migrations.AlterField(
            model_name="facilityinventoryminquantity",
            name="min_quantity",
            field=models.FloatField(
                default=0, validators=[django.core.validators.MinValueValidator(0.0)]
            ),
        ),
    ]
