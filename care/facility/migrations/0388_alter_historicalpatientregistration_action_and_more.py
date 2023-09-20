from django.db import migrations, models


def update_recommend_discharge(apps, schema_editor):
    patient_model = apps.get_model("facility", "PatientRegistration")
    patient_model.objects.filter(
        last_consultation__last_daily_round__recommend_discharge=True
    ).update(action=90)


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0387_merge_20230911_2303"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historicalpatientregistration",
            name="action",
            field=models.IntegerField(
                blank=True,
                choices=[
                    (10, "NO_ACTION"),
                    (20, "PENDING"),
                    (30, "SPECIALIST_REQUIRED"),
                    (40, "PLAN_FOR_HOME_CARE"),
                    (50, "FOLLOW_UP_NOT_REQUIRED"),
                    (60, "COMPLETE"),
                    (70, "REVIEW"),
                    (80, "NOT_REACHABLE"),
                    (90, "DISCHARGE_RECOMMENDED"),
                ],
                default=10,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="patientregistration",
            name="action",
            field=models.IntegerField(
                blank=True,
                choices=[
                    (10, "NO_ACTION"),
                    (20, "PENDING"),
                    (30, "SPECIALIST_REQUIRED"),
                    (40, "PLAN_FOR_HOME_CARE"),
                    (50, "FOLLOW_UP_NOT_REQUIRED"),
                    (60, "COMPLETE"),
                    (70, "REVIEW"),
                    (80, "NOT_REACHABLE"),
                    (90, "DISCHARGE_RECOMMENDED"),
                ],
                default=10,
                null=True,
            ),
        ),
        migrations.RunPython(update_recommend_discharge),
        migrations.RemoveField(
            model_name="dailyround",
            name="recommend_discharge",
        ),
    ]
