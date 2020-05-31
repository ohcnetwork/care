# Generated by Django 2.2.11 on 2020-05-30 16:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("facility", "0008_care_platform"),
    ]

    operations = [
        migrations.RemoveField(model_name="inventoryitem", name="unit",),
        migrations.AlterField(
            model_name="inventoryitem",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="inventoryitem",
            name="name",
            field=models.CharField(max_length=30, unique=True),
        ),
    ]
