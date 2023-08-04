# Generated by Django 4.2.2 on 2023-08-04 10:33

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facility', '0374_historicalpatientregistration_abha_number_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dailyround',
            name='resp',
            field=models.IntegerField(default=None, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(70)]),
        ),
        migrations.AlterField(
            model_name='hospitaldoctors',
            name='count',
            field=models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]
