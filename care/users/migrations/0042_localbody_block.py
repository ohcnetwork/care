# Generated by Django 2.2.11 on 2021-08-23 05:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0041_block'),
    ]

    operations = [
        migrations.AddField(
            model_name='localbody',
            name='block',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='users.Block'),
        ),
    ]
