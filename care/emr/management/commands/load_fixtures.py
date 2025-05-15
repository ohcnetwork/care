import json
import secrets
import uuid
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command
from django.db import transaction
from faker import Faker

from care.emr.models import FacilityOrganization, Organization, Patient, Questionnaire
from care.emr.models.encounter import EncounterOrganization
from care.emr.models.location import FacilityLocationOrganization
from care.emr.models.organization import FacilityOrganizationUser, OrganizationUser
from care.emr.models.questionnaire import QuestionnaireOrganization
from care.emr.resources.device.spec import DeviceCreateSpec
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
from care.emr.resources.location.spec import FacilityLocationWriteSpec
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

# Roles with their user types
ROLES_OPTIONS = {
    "Volunteer": "volunteer",
    "Doctor": "doctor",
    "Staff": "staff",
    "Nurse": "nurse",
    "Administrator": "administrator",
    "Facility Admin": "administrator",
}


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
        self.geo_organization = geo_organization
        self.stdout.write(f"Created geo organization: {geo_organization.name}")

        facility = self._create_facility(fake, super_user, geo_organization)
        self.stdout.write(f"Created facility: {facility.name}")

        external_facility_organization = self._create_facility_organization(
            fake, super_user, facility
        )
        self.stdout.write(
            f"Created facility organization (dept): {external_facility_organization.name}"
        )

        self._create_facility(fake, super_user, geo_organization)
        self.stdout.write("Created resource facility")

        location = self._create_location(
            fake,
            super_user,
            facility,
            [external_facility_organization],
            mode="kind",
            form="wa",
        )
        self.stdout.write(f"Created location: {location.name}")

        for i in range(1, 6):
            bed = self._create_location(
                fake,
                super_user,
                facility,
                [external_facility_organization],
                mode="instance",
                form="bd",
                parent=location.external_id,
                name=f"Bed {i}",
            )
            self.stdout.write(f"Created bed: {bed.name}")

        for i in range(1, 6):
            device = self._create_device(
                fake,
                super_user,
                external_facility_organization,
                name=f"Device {i}",
            )
            self.stdout.write(f"Created device: {device.user_friendly_name}")

        organizations = self._create_organizations(fake, super_user)

        for organization in organizations:
            self.stdout.write(f"Created organization: {organization.name}")

        self._create_default_users(fake, super_user, external_facility_organization)

        self._create_facility_users(
            fake,
            super_user,
            external_facility_organization,
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
            [external_facility_organization],
            options["encounter"],
        )

        self._create_questionnaires(facility, super_user)

    def _create_geo_organization(self, fake, super_user):
        org_spec = OrganizationWriteSpec(
            active=True, org_type=OrganizationTypeChoices.govt, name=fake.state()
        )
        org = org_spec.de_serialize()
        org.created_by = super_user
        org.updated_by = super_user
        org.save()
        return org

    def _create_facility(self, fake, super_user, geo_organization, name=None):
        facility_spec = FacilityCreateSpec(
            geo_organization=geo_organization.external_id,
            name=name or fake.company(),
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

    def _attach_role_organization_user(self, organization, user, role):
        return OrganizationUser.objects.create(
            organization=organization, user=user, role=role
        )

    def _attach_role_facility_organization_user(
        self, facility_organization, user, role
    ):
        return FacilityOrganizationUser.objects.create(
            organization=facility_organization, user=user, role=role
        )

    def _create_user(
        self,
        fake,
        username,
        user_type,
        super_user,
        facility_organization=None,
        geo_organization=None,
        role=None,
        password=None,
    ):
        password = password or fake.password(length=10, special_chars=False)
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
            user_type=user_type,
        )
        user = user_spec.de_serialize()
        user.geo_organization = geo_organization or self.geo_organization
        user.created_by = super_user
        user.updated_by = super_user
        user.save()

        if role:
            if facility_organization:
                self._attach_role_facility_organization_user(
                    facility_organization=facility_organization,
                    user=user,
                    role=role,
                )
                if (
                    user.user_type == "administrator"
                    and facility_organization.facility.default_internal_organization
                ):
                    self._attach_role_facility_organization_user(
                        facility_organization=facility_organization.facility.default_internal_organization,
                        user=user,
                        role=role,
                    )
            if user.geo_organization:
                self._attach_role_organization_user(
                    organization=user.geo_organization,
                    user=user,
                    role=role,
                )
            self._attach_role_organization_user(
                organization=Organization.objects.get(
                    name=role.name, org_type=OrganizationTypeChoices.role
                ),
                user=user,
                role=role,
            )

    def _create_facility_users(
        self,
        fake,
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

        for role_name, user_type in ROLES_OPTIONS.items():
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

                    self._create_user(
                        fake,
                        username=username,
                        user_type=user_type,
                        super_user=super_user,
                        facility_organization=facility_organization,
                        role=role,
                        password=password,
                    )

                    self.stdout.write(f"{role_name:<15} {username:<30} {password:<20}")

            except RoleModel.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Role '{role_name}' not found, skipping.")
                )

        self.stdout.write("=" * 50)

    def _create_default_users(self, fake, super_user, facility_organization):
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

                self._create_user(
                    fake,
                    username=username,
                    user_type=ROLES_OPTIONS[role_name],
                    super_user=super_user,
                    facility_organization=facility_organization,
                    role=role,
                    password=password,
                )

                self.stdout.write(f"{role_name:<15} {username:<30} {password:<20}")
            except RoleModel.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Role '{role_name}' not found, skipping.")
                )

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
        facility_organizations,
        count_per_patient,
    ):
        total = len(patients) * count_per_patient
        self.stdout.write(f"Creating {total} encounters...")

        for patient in patients:
            for _ in range(count_per_patient):
                encounter_spec = EncounterCreateSpec(
                    organizations=[],  # this field is used by the viewset to add the relations
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
                for organization in facility_organizations:
                    EncounterOrganization.objects.create(
                        encounter=encounter,
                        organization=organization,
                    )

    def _create_questionnaires(self, facility, super_user):
        with Path.open("data/questionnaire_fixtures.json") as f:
            questionnaires = json.load(f)

        roles = Organization.objects.filter(
            name__in=ROLES_OPTIONS.keys(), org_type=OrganizationTypeChoices.role
        )

        facility_organizations = FacilityOrganization.objects.filter(
            facility=facility,
        ).values_list("external_id", flat=True)

        for questionnaire in questionnaires:
            questionnaire_slug = questionnaire["slug"]
            if Questionnaire.objects.filter(slug=questionnaire_slug).exists():
                continue

            questionnaire["version"] = questionnaire.get("version") or "1.0"

            questionnaire["organizations"] = facility_organizations
            questionnaire["tags"] = []

            questionnaire_spec = QuestionnaireSpec(**questionnaire)

            questionnaire_spec = questionnaire_spec.de_serialize()

            questionnaire_spec.created_by = super_user
            questionnaire_spec.updated_by = super_user
            questionnaire_spec.save()

            for role in roles:
                QuestionnaireOrganization.objects.create(
                    questionnaire=questionnaire_spec,
                    organization=role,
                )

        self.stdout.write("Questionnaires loaded....")

    def _create_location(
        self,
        fake,
        super_user,
        facility,
        organizations,
        mode,
        form,
        parent=None,
        name=None,
    ):
        location_spec = FacilityLocationWriteSpec(
            organizations=[],  # this field is used by the viewset to add the relations
            parent=parent,
            status="active",
            operational_status="O",
            name=name or fake.company(),
            description=fake.text(max_nb_chars=200),
            mode=mode,
            form=form,
        )
        location = location_spec.de_serialize()
        location.facility = facility
        location.created_by = super_user
        location.updated_by = super_user
        location.save()

        for organization in organizations:
            FacilityLocationOrganization.objects.create(
                location=location, organization=organization
            )
        return location

    def _create_device(
        self,
        fake,
        super_user,
        facility_organization,
        name=None,
    ):
        name = name or fake.company()
        device_spec = DeviceCreateSpec(
            registered_name=name,
            user_friendly_name=name,
            description=fake.text(max_nb_chars=200),
            status="active",
            availability_status="available",
            manufacturer=fake.company(),
        )
        device = device_spec.de_serialize()
        device.facility = facility_organization.facility
        device.managing_organization = facility_organization
        device.created_by = super_user
        device.updated_by = super_user
        device.save()
        return device
