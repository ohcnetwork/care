from django.db import migrations


def populate_patient_consultation(apps, *args):

    patientmodel = apps.get_model("facility", "patientregistration")
    consultationmodel = apps.get_model("facility", "patientconsultation")
    for obj in patientmodel.objects.all():
        consultation = consultationmodel.objects.filter(patient_id=obj.id).order_by("-created_date").first()
        obj.last_consultation = consultation
        obj.save()


def reverse_populate_patient_consultation(apps, *args):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0153_auto_20200805_2226"),
    ]

    operations = [
        migrations.RunPython(populate_patient_consultation, reverse_code=reverse_populate_patient_consultation)
    ]
