# Generated by Django 2.2.11 on 2023-04-18 13:56

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0335_auto_20230207_1914"),
    ]

    operations = [
        migrations.AddField(
            model_name="patientnotes",
            name="editable_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
