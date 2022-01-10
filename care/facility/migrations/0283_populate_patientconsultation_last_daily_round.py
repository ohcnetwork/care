from django.db import migrations


def populate_last_daily_round(apps, *args):
    PatientConsultation = apps.get_model("facility", "PatientConsultation")
    DailyRound = apps.get_model("facility", "DailyRound")
    for consultation in PatientConsultation.objects.all():
        consultation.last_daily_round = DailyRound.objects.filter(
            patient_consultation_id=consultation.id
        ).order_by('-date').first()
        consultation.save()


def reverse_populate_last_daily_round(apps, *args):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0282_patientconsultation_last_daily_round"),
    ]

    operations = [
        migrations.RunPython(
            populate_last_daily_round,
            reverse_code=reverse_populate_last_daily_round
        )
    ]
