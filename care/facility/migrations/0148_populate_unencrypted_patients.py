from django.db import migrations


def populate_patient_unencrypted(apps, *args):

    model = apps.get_model("facility", "patientregistration")
    for obj in model.objects.all():
        obj.name_new = obj.name
        obj.phone_number_new = obj.phone_number
        obj.address_new = obj.address
        obj.save()


def reverse_populate_patient_unencrypted(apps, *args):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0147_auto_20200802_2134"),
    ]

    operations = [
        migrations.RunPython(
            populate_patient_unencrypted,
            reverse_code=reverse_populate_patient_unencrypted,
        )
    ]
