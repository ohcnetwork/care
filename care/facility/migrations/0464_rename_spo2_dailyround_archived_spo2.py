# Generated by Django 5.1.1 on 2024-09-22 19:07

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0463_patientnotes_reply_to"),
    ]

    operations = [
        migrations.RenameField(
            model_name="dailyround",
            old_name="spo2",
            new_name="archived_spo2",
        ),
    ]
