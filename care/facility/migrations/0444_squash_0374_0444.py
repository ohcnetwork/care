# Generated by Django 4.2.10 on 2024-04-21 17:12

# This is a replacement migration for facility.0374 and facility.0428 that creates and removes the abha_number field on PatientRegistration.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0373_remove_patientconsultation_hba1c"),
    ]

    replaces = [
        ("facility", "0374_historicalpatientregistration_abha_number_and_more"),
        ("facility", "0444_remove_historicalpatientregistration_abha_number_and_more"),
    ]

    operations = []
