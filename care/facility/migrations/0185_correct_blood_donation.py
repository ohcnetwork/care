from django.db import migrations


def correct_blood_donation_values(apps, *args):
    patientmodel = apps.get_model("facility", "patientregistration")
    patientmodel.objects.all().update(will_donate_blood=None, fit_for_blood_donation=None)


def reverse_correct_blood_donation_values(apps, *args):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0184_auto_20200925_2353"),
    ]

    operations = [
        migrations.RunPython(correct_blood_donation_values, reverse_code=reverse_correct_blood_donation_values)
    ]
