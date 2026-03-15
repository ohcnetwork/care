import secrets

from django.utils import timezone

from care.emr.models import EncounterOrganization
from care.emr.resources.encounter.constants import (
    ClassChoices,
    EncounterPriorityChoices,
    StatusChoices,
)
from care.emr.resources.encounter.spec import EncounterCreateSpec
from care.emr.resources.patient.spec import (
    BloodGroupChoices,
    GenderChoices,
    PatientCreateSpec,
)

from . import generate_unique_indian_phone_number


def create_patients(fake, super_user, geo_organization, count):
    patients = []
    for _ in range(count):
        patient_spec = PatientCreateSpec(
            name=fake.name(),
            gender=secrets.choice(list(GenderChoices)).value,
            phone_number=generate_unique_indian_phone_number(),
            emergency_phone_number=generate_unique_indian_phone_number(),
            address=fake.address(),
            permanent_address=fake.address(),
            pincode=fake.random_int(min=100000, max=999999),
            blood_group=secrets.choice(list(BloodGroupChoices)).value,
            geo_organization=geo_organization.external_id,
            date_of_birth=fake.date_of_birth(),
        )
        patient = patient_spec.de_serialize()
        patient.created_by = super_user
        patient.updated_by = super_user
        patient.save()
        patients.append(patient)

    return patients


def create_encounters(
    fake,
    super_user,
    patients,
    facility,
    facility_organizations,
    count_per_patient,
):
    encounters = []
    for patient in patients:
        for _ in range(count_per_patient):
            encounter_spec = EncounterCreateSpec(
                organizations=[],
                discharge_summary_advice=fake.paragraph(),
                status=StatusChoices.in_progress,
                encounter_class=secrets.choice(list(ClassChoices)).value,
                patient=patient.external_id,
                facility=facility.external_id,
                priority=secrets.choice(list(EncounterPriorityChoices)).value,
                period={
                    "start": str(
                        timezone.make_aware(
                            fake.date_time_this_year(before_now=True)
                        )
                    ),
                },
            )
            encounter = encounter_spec.de_serialize()
            encounter.created_by = super_user
            encounter.updated_by = super_user
            encounter.save()
            for organization in facility_organizations:
                EncounterOrganization.objects.create(
                    encounter=encounter,
                    organization=organization,
                )
            encounters.append(encounter)

    return encounters
