# Generated by Django 2.2.11 on 2020-03-22 14:11

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('facility', '0014_delete_facilitylocation'),
    ]

    operations = [
        migrations.AddField(
            model_name='facility',
            name='location',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326),
        ),
    ]
