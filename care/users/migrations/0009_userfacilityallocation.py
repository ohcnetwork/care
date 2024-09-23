# Generated by Django 4.2.2 on 2023-07-12 12:27

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def fill_user_facility_allocation(apps, _):
    UserFacilityAllocation = apps.get_model("users", "UserFacilityAllocation")
    User = apps.get_model("users", "User")
    users = User.objects.filter(home_facility__isnull=False)

    to_create = [
        UserFacilityAllocation(
            user=user, facility=user.home_facility, start_date=user.date_joined
        )
        for user in users
    ]
    UserFacilityAllocation.objects.bulk_create(to_create, batch_size=2000)


def reverse_fill_user_facility_allocation(apps, _):
    UserFacilityAllocation = apps.get_model("users", "UserFacilityAllocation")
    UserFacilityAllocation.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0370_merge_20230705_1500"),
        ("users", "0008_rename_skill_and_add_new_20230817_1937"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserFacilityAllocation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("start_date", models.DateTimeField(default=django.utils.timezone.now)),
                ("end_date", models.DateTimeField(blank=True, null=True)),
                (
                    "facility",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="facility.facility",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.RunPython(
            fill_user_facility_allocation, reverse_fill_user_facility_allocation
        ),
    ]
