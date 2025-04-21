import json
import secrets
import uuid
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command
from django.db import transaction
from faker import Faker

from care.emr.models import FacilityOrganization, Organization, Patient, Questionnaire
from care.emr.resources.encounter.constants import (
    ClassChoices,
    EncounterPriorityChoices,
    StatusChoices,
)
from care.emr.resources.encounter.spec import EncounterCreateSpec
from care.emr.resources.facility.spec import FacilityCreateSpec
from care.emr.resources.facility_organization.spec import (
    FacilityOrganizationTypeChoices,
    FacilityOrganizationWriteSpec,
)
from care.emr.resources.organization.spec import (
    OrganizationTypeChoices,
    OrganizationWriteSpec,
)
from care.emr.resources.patient.spec import (
    BloodGroupChoices,
    GenderChoices,
    PatientCreateSpec,
)
from care.emr.resources.questionnaire.spec import QuestionnaireSpec
from care.emr.resources.user.spec import UserCreateSpec
from care.security.models import RoleModel
from care.users.models import User
from care.utils.tests.base import CareAPITestBase

ROLES_OPTIONS = [
    "Volunteer",
    "Doctor",
    "Staff",
    "Nurse",
    "Administrator",
    "Facility Admin",
]


def generate_unique_indian_phone_number():
    return (
        "+91"
        + secrets.choice(["9", "8", "7", "6"])
        + "".join([str(secrets.randbelow(10)) for _ in range(9)])
    )


class Command(BaseCommand):
    help = "Generate test fixtures for the backend"

    def add_arguments(self, parser):
        parser.add_argument(
            "--users", type=int, default=1, help="Number of each type of users"
        )
        parser.add_argument(
            "--patients", type=int, default=10, help="Number of patients"
        )
        parser.add_argument(
            "--encounter", type=int, default=1, help="Number of encounters per patient"
        )
        parser.add_argument(
            "--default-password",
            type=str,
            default="Coronasafe@123",
            help="Set a default password for all users (easier for testing)",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stdout.write(
                self.style.ERROR(
                    "This command should not be run in production. Exiting..."
                )
            )
            return

        self.stdout.write("Starting fixtures generation...")

        self.stdout.write("Syncing permissions and valuesets...")
        call_command("sync_permissions_roles")
        call_command("sync_valueset")

        try:
            with transaction.atomic():
                self._generate_fixtures(options)
                self.stdout.write(
                    self.style.SUCCESS(
                        "Successfully generated all fixtures in transaction!"
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Transaction rolled back due to error: {e}")
            )
            raise

    def _generate_fixtures(self, options):
        """Generate all the fixture data within a transaction context."""
        base = CareAPITestBase()
        fake = Faker("en_IN")

        super_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "user_type": "admin",
                "is_superuser": True,
                "is_staff": True,
                "first_name": "Admin",
                "last_name": "User",
            },
        )
        if created:
            super_user.set_password("admin")
            super_user.save()

        self.stdout.write("=" * 30)
        if created:
            self.stdout.write("Superuser username: admin")
            self.stdout.write("Superuser password: admin")
        else:
            self.stdout.write(
                "Superuser 'admin' already exists, not creating a new one."
            )
        self.stdout.write("=" * 30)

        geo_organization = self._create_geo_organization(fake, super_user)
        self.stdout.write(f"Created geo organization: {geo_organization.name}")

        facility = self._create_facility(fake, super_user, geo_organization)
        self.stdout.write(f"Created facility: {facility.name}")

        facility_organization = FacilityOrganization.objects.filter(
            facility=facility
        ).first()

        external_facility_organization = self._create_facility_organization(
            fake, super_user, facility
        )
        self.stdout.write(
            f"Created facility organization (dept): {external_facility_organization.name}"
        )

        organizations = self._create_organizations(fake, super_user)

        for organization in organizations:
            self.stdout.write(f"Created organization: {organization.name}")

        self._create_default_users(fake, base, super_user, facility_organization)

        self._create_users(
            fake,
            base,
            super_user,
            facility_organization,
            options["users"],
            options["default_password"],
        )

        patients = self._create_patients(
            fake, super_user, geo_organization, options["patients"]
        )

        self._create_encounters(
            fake,
            super_user,
            patients,
            facility,
            facility_organization,
            options["encounter"],
        )

        self._create_questionnaires(facility_organization, super_user)

    def _create_geo_organization(self, fake, super_user):
        org_spec = OrganizationWriteSpec(
            active=True, org_type=OrganizationTypeChoices.govt, name=fake.state()
        )
        org = org_spec.de_serialize()
        org.created_by = super_user
        org.updated_by = super_user
        org.save()
        return org

    def _create_facility(self, fake, super_user, geo_organization):
        facility_spec = FacilityCreateSpec(
            geo_organization=geo_organization.external_id,
            name=fake.company(),
            description=fake.text(max_nb_chars=200),
            longitude=float(fake.longitude()),
            latitude=float(fake.latitude()),
            pincode=fake.random_int(min=100000, max=999999),
            address=fake.address(),
            phone_number=generate_unique_indian_phone_number(),
            middleware_address=fake.address(),
            facility_type="Private Hospital",
            is_public=True,
            features=[1],
        )
        facility = facility_spec.de_serialize()
        facility.created_by = super_user
        facility.updated_by = super_user
        facility.save()
        return facility

    def _create_facility_organization(self, fake, super_user, facility):
        org_spec = FacilityOrganizationWriteSpec(
            active=True,
            name=fake.company(),
            description=fake.text(max_nb_chars=200),
            facility=facility.external_id,
            org_type=FacilityOrganizationTypeChoices.dept,
        )
        org = org_spec.de_serialize()
        org.created_by = super_user
        org.updated_by = super_user
        org.save()
        return org

    def _create_organizations(self, fake, super_user):
        orgs = []
        for role_name in ROLES_OPTIONS:
            if Organization.objects.filter(
                name=role_name, org_type=OrganizationTypeChoices.role
            ).exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"Organization '{role_name}' already exists, skipping."
                    )
                )
                continue
            org_spec = OrganizationWriteSpec(
                active=True, org_type=OrganizationTypeChoices.role, name=role_name
            )
            org = org_spec.de_serialize()
            org.created_by = super_user
            org.updated_by = super_user
            org.save()
            orgs.append(org)
        return orgs

    def _create_users(
        self,
        fake,
        base,
        super_user,
        facility_organization,
        count,
        default_password=None,
    ):
        self.stdout.write("=" * 50)
        self.stdout.write("USER CREDENTIALS")
        self.stdout.write("=" * 50)
        self.stdout.write(f"{'ROLE':<15} {'USERNAME':<30} {'PASSWORD':<20}")
        self.stdout.write("-" * 65)

        for role_name in ROLES_OPTIONS:
            try:
                role = RoleModel.objects.get(name=role_name)

                for i in range(count):
                    password = default_password or fake.password(
                        length=10, special_chars=False
                    )
                    username = (
                        f"{role_name.lower()}_{facility_organization.id}_{i}".replace(
                            " ", "_"
                        )
                    )

                    user_spec = UserCreateSpec(
                        first_name=fake.first_name(),
                        last_name=fake.last_name(),
                        phone_number=generate_unique_indian_phone_number(),
                        prefix=fake.prefix(),
                        suffix=fake.suffix(),
                        gender=secrets.choice(list(GenderChoices)).value,
                        password=password,
                        username=username,
                        email=str(uuid.uuid4()) + fake.email(),
                        user_type=role_name.lower().replace(" ", "_"),
                    )
                    user = user_spec.de_serialize()
                    user.created_by = super_user
                    user.updated_by = super_user
                    user.save()

                    self.stdout.write(f"{role_name:<15} {username:<30} {password:<20}")

                    base.attach_role_facility_organization_user(
                        facility_organization=facility_organization,
                        user=user,
                        role=role,
                    )
            except RoleModel.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Role '{role_name}' not found, skipping.")
                )

        self.stdout.write("=" * 50)

    def _create_patients(
        self, fake, super_user, geo_organization, count
    ) -> list[Patient]:
        patients = []
        self.stdout.write(f"Creating {count} patients...")

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

    def _create_encounters(
        self,
        fake,
        super_user,
        patients,
        facility,
        facility_organization,
        count_per_patient,
    ):
        total = len(patients) * count_per_patient
        self.stdout.write(f"Creating {total} encounters...")

        for patient in patients:
            for _ in range(count_per_patient):
                encounter_spec = EncounterCreateSpec(
                    organizations=[facility_organization.external_id],
                    discharge_summary_advice=fake.paragraph(),
                    status=StatusChoices.in_progress,
                    encounter_class=secrets.choice(list(ClassChoices)).value,
                    patient=patient.external_id,
                    facility=facility.external_id,
                    priority=secrets.choice(list(EncounterPriorityChoices)).value,
                )
                encounter = encounter_spec.de_serialize()
                encounter.created_by = super_user
                encounter.updated_by = super_user
                encounter.save()

    def _create_questionnaires(self, facility_organization, super_user):
        with Path.open("data/questionnaire_fixtures.json") as f:
            questionnaires = json.load(f)

        for questionnaire in questionnaires:
            questionnaire_slug = questionnaire["slug"]
            if Questionnaire.objects.filter(slug=questionnaire_slug).exists():
                continue

            questionnaire["version"] = questionnaire.get("version") or "1.0"

            questionnaire["organizations"] = [facility_organization.external_id]
            questionnaire["tags"] = []

            questionnaire_spec = QuestionnaireSpec(**questionnaire)

            questionnaire_spec = questionnaire_spec.de_serialize()

            questionnaire_spec.created_by = super_user
            questionnaire_spec.updated_by = super_user
            questionnaire_spec.save()

        self.stdout.write("Questionnaires loaded....")

    def _create_default_users(self, fake, base, super_user, facility_organization):
        fixed_users = [
            ("Doctor", "care-doctor"),
            ("Staff", "care-staff"),
            ("Nurse", "care-nurse"),
            ("Administrator", "care-admin"),
            ("Volunteer", "care-volunteer"),
            ("Facility Admin", "care-fac-admin"),
        ]

        password = "Ohcn@123"
        for role_name, username in fixed_users:
            try:
                role = RoleModel.objects.get(name=role_name)

                if User.objects.filter(username=username).exists():
                    self.stdout.write(
                        self.style.WARNING(f"User {username} already exists. Skipping.")
                    )
                    continue

                user_spec = UserCreateSpec(
                    first_name=username.split("-")[1].capitalize(),
                    last_name="User",
                    phone_number=generate_unique_indian_phone_number(),
                    prefix=fake.prefix(),
                    suffix=fake.suffix(),
                    gender=secrets.choice(list(GenderChoices)).value,
                    password=password,
                    username=username,
                    email=f"{username}@example.com",
                    user_type=role_name.lower().replace(" ", "_"),
                )
                user = user_spec.de_serialize()
                user.created_by = super_user
                user.updated_by = super_user
                user.save()

                base.attach_role_facility_organization_user(
                    facility_organization=facility_organization,
                    user=user,
                    role=role,
                )

                self.stdout.write(f"{role_name:<15} {username:<30} {password:<20}")
            except RoleModel.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Role '{role_name}' not found, skipping.")
                )
