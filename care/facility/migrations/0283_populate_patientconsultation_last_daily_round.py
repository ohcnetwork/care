from django.db import migrations


def populate_last_daily_round(apps, *args):
    PatientConsultation = apps.get_model("facility", "PatientConsultation")
    DailyRound = apps.get_model("facility", "DailyRound")
    consultations = PatientConsultation.objects.all()
    for consultation in consultations:
        consultation.last_daily_round = DailyRound.objects.filter(
            consultation_id=consultation.id
        ).order_by('-created_date').first()
    PatientConsultation.objects.bulk_update(
        consultations, ['last_daily_round'])


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
