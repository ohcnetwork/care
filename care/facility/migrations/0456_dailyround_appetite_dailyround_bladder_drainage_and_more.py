# Generated by Django 4.2.10 on 2024-09-13 07:06

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0455_remove_facility_old_features"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailyround",
            name="appetite",
            field=models.SmallIntegerField(
                blank=True,
                choices=[
                    (1, "INCREASED"),
                    (2, "SATISFACTORY"),
                    (3, "REDUCED"),
                    (4, "NO_TASTE_FOR_FOOD"),
                    (5, "CANNOT_BE_ASSESSED"),
                ],
                default=None,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="dailyround",
            name="bladder_drainage",
            field=models.SmallIntegerField(
                blank=True,
                choices=[
                    (1, "NORMAL"),
                    (2, "CONDOM_CATHETER"),
                    (3, "DIAPER"),
                    (4, "INTERMITTENT_CATHETER"),
                    (5, "CONTINUOUS_INDWELLING_CATHETER"),
                    (6, "CONTINUOUS_SUPRAPUBIC_CATHETER"),
                    (7, "UROSTOMY"),
                ],
                default=None,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="dailyround",
            name="bladder_issue",
            field=models.SmallIntegerField(
                blank=True,
                choices=[
                    (0, "NO_ISSUES"),
                    (1, "INCONTINENCE"),
                    (2, "RETENTION"),
                    (3, "HESITANCY"),
                ],
                default=None,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="dailyround",
            name="bowel_issue",
            field=models.SmallIntegerField(
                blank=True,
                choices=[(0, "NO_DIFFICULTY"), (1, "CONSTIPATION"), (2, "DIARRHOEA")],
                default=None,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="dailyround",
            name="is_experiencing_dysuria",
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="dailyround",
            name="nutrition_route",
            field=models.SmallIntegerField(
                blank=True,
                choices=[
                    (1, "ORAL"),
                    (2, "RYLES_TUBE"),
                    (3, "GASTROSTOMY_OR_JEJUNOSTOMY"),
                    (4, "PEG"),
                    (5, "PARENTERAL_TUBING_FLUID"),
                    (6, "PARENTERAL_TUBING_TPN"),
                ],
                default=None,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="dailyround",
            name="oral_issue",
            field=models.SmallIntegerField(
                blank=True,
                choices=[(0, "NO_ISSUE"), (1, "DYSPHAGIA"), (2, "ODYNOPHAGIA")],
                default=None,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="dailyround",
            name="sleep",
            field=models.SmallIntegerField(
                blank=True,
                choices=[
                    (1, "EXCESSIVE"),
                    (2, "SATISFACTORY"),
                    (3, "UNSATISFACTORY"),
                    (4, "NO_SLEEP"),
                ],
                default=None,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="dailyround",
            name="urination_frequency",
            field=models.SmallIntegerField(
                blank=True,
                choices=[(1, "NORMAL"), (2, "DECREASED"), (3, "INCREASED")],
                default=None,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="dailyround",
            name="rounds_type",
            field=models.IntegerField(
                choices=[
                    (0, "NORMAL"),
                    (30, "COMMUNITY_NURSES_LOG"),
                    (50, "DOCTORS_LOG"),
                    (100, "VENTILATOR"),
                    (200, "ICU"),
                    (300, "AUTOMATED"),
                    (400, "TELEMEDICINE"),
                ],
                default=0,
            ),
        ),
    ]
