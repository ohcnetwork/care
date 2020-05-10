from uuid import uuid4

from django.db import migrations


def unique_external_ids(apps, *args):

    models = [
        "ambulance",
        "ambulancedriver",
        "building",
        "facility",
        "facilitycapacity",
        "facilitypatientstatshistory",
        "facilitystaff",
        "facilityvolunteer",
        "historicalfacilitycapacity",
        "hospitaldoctors",
        "inventory",
        "inventoryitem",
        "inventorylog",
        "patientconsultation",
        "patientsample",
        "patientsampleflow",
        "room",
        "staffroomallocation",
    ]
    for i in models:
        model = apps.get_model("facility", i)
        for obj in model.objects.all():
            obj.external_id = uuid4()
            obj.save()


def reverse_unique_external_ids(apps, *args):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0106_auto_20200510_1557"),
    ]

    operations = [migrations.RunPython(unique_external_ids, reverse_code=reverse_unique_external_ids)]
