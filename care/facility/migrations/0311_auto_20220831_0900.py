import django.core.validators
from django.db import migrations, models
import django.db.models.deletion

from care.facility.models.patient import PatientHealthDetails, PatientConsultation


def populate_data(apps, schema_editor):
    PatientConsultationModel = apps.get_model("facility", "PatientConsultation")
    patients_cons = PatientConsultationModel.objects.all()

    for patient_cons in patients_cons:
        try:
            health_details = PatientHealthDetails.objects.get(
                id=patient_cons.patient.id
            )
            if patient_cons.weight:
                health_details.weight = patient_cons.weight

            if patient_cons.height:
                health_details.height = patient_cons.height

            health_details.created_in_consultation = PatientConsultation.objects.get(
                id=patient_cons.id
            )

            health_details.save()
        except PatientHealthDetails.DoesNotExist:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ("facility", "0310_auto_20220813_1123"),
    ]

    operations = [
        migrations.AddField(
            model_name="patienthealthdetails",
            name="created_in_consultation",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="facility.PatientConsultation",
            ),
        ),
        migrations.AddField(
            model_name="patientconsultation",
            name="last_health_details",
            field=models.ForeignKey(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="facility.PatientHealthDetails",
            ),
        ),
        migrations.AddField(
            model_name="patienthealthdetails",
            name="height",
            field=models.FloatField(
                default=None,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Patient's Height in CM",
            ),
        ),
        migrations.AddField(
            model_name="patienthealthdetails",
            name="weight",
            field=models.FloatField(
                default=None,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Patient's Weight in KG",
            ),
        ),
        migrations.RunPython(populate_data, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="patientconsultation",
            name="height",
        ),
        migrations.RemoveField(
            model_name="patientconsultation",
            name="weight",
        ),
    ]
