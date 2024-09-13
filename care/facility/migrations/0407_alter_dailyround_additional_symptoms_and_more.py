# Generated by Django 4.2.5 on 2024-01-08 17:26

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0406_merge_20240116_2346"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dailyround",
            name="additional_symptoms",
            field=models.CharField(
                blank=True,
                choices=[
                    (1, "ASYMPTOMATIC"),
                    (2, "FEVER"),
                    (3, "SORE THROAT"),
                    (4, "COUGH"),
                    (5, "BREATHLESSNESS"),
                    (6, "MYALGIA"),
                    (7, "ABDOMINAL DISCOMFORT"),
                    (8, "VOMITING"),
                    (9, "OTHERS"),
                    (11, "SPUTUM"),
                    (12, "NAUSEA"),
                    (13, "CHEST PAIN"),
                    (14, "HEMOPTYSIS"),
                    (15, "NASAL DISCHARGE"),
                    (16, "BODY ACHE"),
                    (17, "DIARRHOEA"),
                    (18, "PAIN"),
                    (19, "PEDAL EDEMA"),
                    (20, "WOUND"),
                    (21, "CONSTIPATION"),
                    (22, "HEAD ACHE"),
                    (23, "BLEEDING"),
                    (24, "DIZZINESS"),
                    (25, "CHILLS"),
                    (26, "GENERAL WEAKNESS"),
                    (27, "IRRITABILITY"),
                    (28, "CONFUSION"),
                    (29, "ABDOMINAL PAIN"),
                    (30, "JOINT PAIN"),
                    (31, "REDNESS OF EYES"),
                    (32, "ANOREXIA"),
                    (33, "NEW LOSS OF TASTE"),
                    (34, "NEW LOSS OF SMELL"),
                ],
                default=1,
                max_length=89,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="patientconsultation",
            name="symptoms",
            field=models.CharField(
                blank=True,
                choices=[
                    (1, "ASYMPTOMATIC"),
                    (2, "FEVER"),
                    (3, "SORE THROAT"),
                    (4, "COUGH"),
                    (5, "BREATHLESSNESS"),
                    (6, "MYALGIA"),
                    (7, "ABDOMINAL DISCOMFORT"),
                    (8, "VOMITING"),
                    (9, "OTHERS"),
                    (11, "SPUTUM"),
                    (12, "NAUSEA"),
                    (13, "CHEST PAIN"),
                    (14, "HEMOPTYSIS"),
                    (15, "NASAL DISCHARGE"),
                    (16, "BODY ACHE"),
                    (17, "DIARRHOEA"),
                    (18, "PAIN"),
                    (19, "PEDAL EDEMA"),
                    (20, "WOUND"),
                    (21, "CONSTIPATION"),
                    (22, "HEAD ACHE"),
                    (23, "BLEEDING"),
                    (24, "DIZZINESS"),
                    (25, "CHILLS"),
                    (26, "GENERAL WEAKNESS"),
                    (27, "IRRITABILITY"),
                    (28, "CONFUSION"),
                    (29, "ABDOMINAL PAIN"),
                    (30, "JOINT PAIN"),
                    (31, "REDNESS OF EYES"),
                    (32, "ANOREXIA"),
                    (33, "NEW LOSS OF TASTE"),
                    (34, "NEW LOSS OF SMELL"),
                ],
                default=1,
                max_length=89,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="patientteleconsultation",
            name="symptoms",
            field=models.CharField(
                choices=[
                    (1, "ASYMPTOMATIC"),
                    (2, "FEVER"),
                    (3, "SORE THROAT"),
                    (4, "COUGH"),
                    (5, "BREATHLESSNESS"),
                    (6, "MYALGIA"),
                    (7, "ABDOMINAL DISCOMFORT"),
                    (8, "VOMITING"),
                    (9, "OTHERS"),
                    (11, "SPUTUM"),
                    (12, "NAUSEA"),
                    (13, "CHEST PAIN"),
                    (14, "HEMOPTYSIS"),
                    (15, "NASAL DISCHARGE"),
                    (16, "BODY ACHE"),
                    (17, "DIARRHOEA"),
                    (18, "PAIN"),
                    (19, "PEDAL EDEMA"),
                    (20, "WOUND"),
                    (21, "CONSTIPATION"),
                    (22, "HEAD ACHE"),
                    (23, "BLEEDING"),
                    (24, "DIZZINESS"),
                    (25, "CHILLS"),
                    (26, "GENERAL WEAKNESS"),
                    (27, "IRRITABILITY"),
                    (28, "CONFUSION"),
                    (29, "ABDOMINAL PAIN"),
                    (30, "JOINT PAIN"),
                    (31, "REDNESS OF EYES"),
                    (32, "ANOREXIA"),
                    (33, "NEW LOSS OF TASTE"),
                    (34, "NEW LOSS OF SMELL"),
                ],
                max_length=89,
            ),
        ),
    ]
