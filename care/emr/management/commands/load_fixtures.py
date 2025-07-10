import json
import secrets
import sys
import uuid
from decimal import Decimal, localcontext
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command
from django.db import transaction
from faker import Faker
from faker.providers.geo import Provider as GeoProvider

from care.emr.models import FacilityOrganization, Organization, Patient, Questionnaire
from care.emr.models.encounter import EncounterOrganization
from care.emr.models.location import FacilityLocationOrganization
from care.emr.models.organization import FacilityOrganizationUser, OrganizationUser
from care.emr.models.questionnaire import QuestionnaireOrganization
from care.emr.resources.activity_definition.spec import BaseActivityDefinitionSpec
from care.emr.resources.charge_item_definition.spec import ChargeItemDefinitionSpec
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
from care.emr.resources.healthcare_service.spec import BaseHealthcareServiceSpec
from care.emr.resources.location.spec import FacilityLocationWriteSpec
from care.emr.resources.observation_definition.spec import BaseObservationDefinitionSpec
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
from care.emr.resources.specimen_definition.spec import BaseSpecimenDefinitionSpec
from care.emr.resources.user.spec import UserCreateSpec
from care.security.models import RoleModel
from care.users.models import User

# Override the validate_valueset function to skip validation for fixtures
import care.emr.utils.valueset_coding_type  # noqa  # isort:skip

sys.modules["care.emr.utils.valueset_coding_type"].validate_valueset = (
    lambda _, __, code: code
)


def safe_coordinate(self, center=None, radius=0.001):
    with localcontext() as ctx:
        ctx.prec = 10
        if center is None:
            return Decimal(
                str(self.generator.random.randint(-180000000, 180000000) / 1000000)
            ).quantize(Decimal(".000001"))
        center = float(center)
        radius = float(radius)
        geo = self.generator.random.uniform(center - radius, center + radius)
        return Decimal(str(geo)).quantize(Decimal(".000001"))


# Monkey patching the coordinate method of Faker's GeoProvider as it conflicts with our Decimal precision settings
GeoProvider.coordinate = safe_coordinate


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
        self.fake = fake

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
            super_user,
            facility,
            [external_facility_organization],
            mode="kind",
            form="wa",
        )
        self.stdout.write(f"Created location: {location.name}")

        self._create_lab_definition_objects_for_facility(facility, super_user)
        self.stdout.write("Created lab objects for facility")

        for i in range(1, 6):
            bed = self._create_location(
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
            name=name or self.fake.company(),
            description=self.fake.text(max_nb_chars=200),
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

    def _create_lab_definition_objects_for_facility(self, facility, user=None):  # noqa: PLR0915
        def __create_object(model, **kwargs):
            obj = model.de_serialize()
            obj.facility = facility
            obj.created_by = user or facility.created_by
            obj.updated_by = user or facility.updated_by
            for key, value in kwargs.items():
                setattr(obj, key, value)
            obj.save()
            return obj

        bio_chemistry_lab_location = self._create_location(
            user or facility.created_by,
            facility,
            [facility.default_internal_organization],
            mode="kind",
            form="ro",
            name="Bio-Chemistry Lab",
        )

        code_ucum_ml = {
            "code": "mL",
            "system": "http://unitsofmeasure.org",
            "display": "milliliter",
        }
        code_ucum_h = {
            "code": "h",
            "system": "http://unitsofmeasure.org",
            "display": "hours",
        }
        code_ucum_g_dl = {
            "code": "g/dL",
            "system": "http://unitsofmeasure.org",
            "display": "gram per deciliter",
        }
        code_ucum_d = {
            "code": "d",
            "system": "http://unitsofmeasure.org",
            "display": "days",
        }
        code_ucum_percent = {
            "code": "%",
            "system": "http://unitsofmeasure.org",
            "display": "percent",
        }
        code_ucum_million_per_ul = {
            "code": "10*6/uL",
            "system": "http://unitsofmeasure.org",
            "display": "million per microliter",
        }
        code_ucum_thousands_per_ul = {
            "code": "10*3/uL",
            "system": "http://unitsofmeasure.org",
            "display": "Thousands Per MicroLiter",
        }
        code_hl7_bldv = {
            "code": "BLDV",
            "system": "http://terminology.hl7.org/CodeSystem/v2-0487",
            "display": "Blood venous",
        }
        code_hl7_ur = {
            "code": "UR",
            "system": "http://terminology.hl7.org/CodeSystem/v2-0487",
            "display": "Urine",
        }
        code_hl7_grey_cap = {
            "code": "grey",
            "system": "http://terminology.hl7.org/CodeSystem/container-cap",
            "display": "grey cap",
        }
        code_hl7_lavender_cap = {
            "code": "lavender",
            "system": "http://terminology.hl7.org/CodeSystem/container-cap",
            "display": "lavender cap",
        }
        code_hl7_yellow_cap = {
            "code": "yellow",
            "system": "http://terminology.hl7.org/CodeSystem/container-cap",
            "display": "yellow cap",
        }
        code_hl7_dark_yellow_cap = {
            "code": "dark-yellow",
            "system": "http://terminology.hl7.org/CodeSystem/container-cap",
            "display": "dark yellow cap",
        }
        code_snomed_after_fasting = {
            "code": "726054005",
            "system": "http://snomed.info/sct",
            "display": "After fasting",
        }
        code_snomed_same_day_before_procedure = {
            "code": "47531000087108",
            "system": "http://snomed.info/sct",
            "display": "Same day but before procedure",
        }
        code_snomed_puncture = {
            "code": "129300006",
            "system": "http://snomed.info/sct",
            "display": "Puncture - action",
        }
        code_snomed_urine_clean_catch = {
            "code": "73416001",
            "system": "http://snomed.info/sct",
            "display": "Urine specimen collection, clean catch",
        }
        code_snomed_automated_count = {
            "code": "702659008",
            "system": "http://snomed.info/sct",
            "display": "Automated count",
        }
        code_snomed_urine_dipstick = {
            "code": "167226008",
            "system": "http://snomed.info/sct",
            "display": "Urine dipstick test",
        }
        code_snomed_cbc = {
            "code": "26604007",
            "system": "http://snomed.info/sct",
            "display": "Complete blood count",
        }
        code_snomed_fasting_glucose = {
            "code": "271062006",
            "system": "http://snomed.info/sct",
            "display": "Fasting blood glucose measurement",
        }
        code_loinc_fasting_glucose = {
            "code": "1558-6",
            "system": "http://loinc.org",
            "display": "Fasting glucose [Mass/volume] in Serum or Plasma",
        }
        code_loinc_cbc_panel = {
            "code": "58410-2",
            "system": "http://loinc.org",
            "display": "CBC panel - Blood by Automated count",
        }
        code_loinc_hemoglobin = {
            "code": "LP32067-8",
            "system": "http://loinc.org",
            "display": "Hemoglobin",
        }
        code_loinc_hematocrit = {
            "code": "LP15101-6",
            "system": "http://loinc.org",
            "display": "Hematocrit",
        }
        code_loinc_erythrocytes = {
            "code": "LA12896-9",
            "system": "http://loinc.org",
            "display": "Erythrocytes",
        }
        code_loinc_platelets = {
            "code": "LP7631-7",
            "system": "http://loinc.org",
            "display": "Platelets",
        }
        code_loinc_lipid_panel = {
            "code": "LP97557-0",
            "system": "http://loinc.org",
            "display": "Lipid panel with direct LDL",
        }
        code_loinc_urine = {
            "code": "LP7681-2",
            "system": "http://loinc.org",
            "display": "Urine",
        }
        code_loinc_fasting_glucose_serum = {
            "code": "1558-6",
            "system": "http://loinc.org",
            "display": "Fasting glucose [Mass/volume] in Serum or Plasma",
        }

        blood_glucose_specimen_definition = __create_object(
            BaseSpecimenDefinitionSpec(
                slug="blood-glucose-test-specimen",
                title="Blood Glucose Test Specimen",
                status="active",
                description="A venous blood specimen collected for the quantitative measurement of glucose concentration in blood. Used in diagnosis and monitoring of diabetes mellitus and glucose metabolism disorders.",
                type_collected=code_hl7_bldv,
                patient_preparation=[code_snomed_after_fasting],
                collection=code_snomed_puncture,
                type_tested={
                    "container": {
                        "cap": code_hl7_grey_cap,
                        "capacity": {"unit": code_ucum_ml, "value": 5.0},
                        "description": "Grey-top collection tube containing sodium fluoride/potassium oxalate.",
                        "preparation": "Label tube immediately after collection. Invert gently 8-10 times to mix anticoagulant. Transport to lab under cold conditions (2-8°C) if processing is delayed.",
                        "minimum_volume": {
                            "quantity": {"unit": code_ucum_ml, "value": 2.0}
                        },
                    },
                    "is_derived": False,
                    "preference": "preferred",
                    "single_use": False,
                    "requirement": "Refrigerated (2-8°C). Specimen must be centrifuged and plasma separated within 2 hours of collection if not using fluoride tube. For accurate glucose measurement, immediate processing or use of glycolysis inhibitor tubes (e.g., sodium fluoride/potassium oxalate) is recommended.",
                    "retention_time": {"unit": code_ucum_h, "value": 24},
                },
            )
        )
        cbc_specimen_definition = __create_object(
            BaseSpecimenDefinitionSpec(
                slug="cbc-blood",
                title="CBC Blood Specimen",
                status="active",
                description="Whole blood specimen collected via venipuncture for performing a Complete Blood Count (CBC) test.",
                type_collected=code_hl7_bldv,
                patient_preparation=[],
                collection=code_snomed_puncture,
                type_tested={
                    "container": {
                        "cap": code_hl7_lavender_cap,
                        "capacity": {"unit": code_ucum_ml, "value": 10.0},
                        "description": "Purple top EDTA tube",
                        "preparation": "Invert gently 8-10 times immediately after collection to mix with anticoagulant.",
                        "minimum_volume": {
                            "quantity": {"unit": code_ucum_ml, "value": 3.0}
                        },
                    },
                    "is_derived": True,
                    "preference": "preferred",
                    "single_use": True,
                    "requirement": "Collected in EDTA tube to prevent clotting.\nShould be processed within 6 hours of collection.",
                    "retention_time": {"unit": code_ucum_h, "value": 6},
                },
            )
        )
        lipid_panel_specimen_definition = __create_object(
            BaseSpecimenDefinitionSpec(
                slug="lipid-panel-blood-specimen",
                title="Lipid Panel Blood Specimen",
                status="active",
                description="Venous blood specimen collected to evaluate cholesterol levels including total cholesterol, HDL, LDL, and triglycerides.",
                type_collected=code_hl7_bldv,
                patient_preparation=[code_snomed_after_fasting],
                collection=code_snomed_puncture,
                type_tested={
                    "container": {
                        "cap": code_hl7_dark_yellow_cap,
                        "capacity": {"unit": code_ucum_ml, "value": 5.0},
                        "description": "Serum separator tube (SST, Gold-top)",
                        "preparation": "Invert tube gently 5-6 times. Let stand upright for clotting. Centrifuge within 1 hour of collection.",
                        "minimum_volume": {
                            "quantity": {"unit": code_ucum_ml, "value": 2.0}
                        },
                    },
                    "is_derived": False,
                    "preference": "preferred",
                    "single_use": True,
                    "requirement": "Refrigerated (2-8°C). Allow blood to clot at room temperature for 30 minutes. Centrifuge and separate serum promptly.",
                    "retention_time": {"unit": code_ucum_d, "value": 7},
                },
            )
        )
        urinalysis_specimen_definition = __create_object(
            BaseSpecimenDefinitionSpec(
                slug="urinalysis-specimen",
                title="Urinalysis Specimen",
                status="active",
                description="Midstream clean-catch urine specimen collected for analysis of physical, chemical, and microscopic properties.",
                type_collected=code_hl7_ur,
                patient_preparation=[code_snomed_same_day_before_procedure],
                collection=code_snomed_urine_clean_catch,
                type_tested={
                    "container": {
                        "cap": code_hl7_yellow_cap,
                        "capacity": {"unit": code_ucum_ml, "value": 100.0},
                        "description": "Sterile urine collection container with screw cap.",
                        "preparation": "Label container. Ensure tight seal to avoid contamination or leakage.",
                        "minimum_volume": {
                            "quantity": {"unit": code_ucum_ml, "value": 30.0}
                        },
                    },
                    "is_derived": False,
                    "preference": "preferred",
                    "single_use": False,
                    "requirement": "Up to 24 hours refrigerated. Deliver to lab within 2 hours of collection. If delayed, refrigerate immediately.",
                    "retention_time": {"unit": code_ucum_h, "value": 2},
                },
            )
        )

        fasting_blood_glucose_observation_definition = __create_object(
            BaseObservationDefinitionSpec(
                slug="fasting_blood_glucose",
                title="Fasting Blood Glucose",
                status="active",
                description="Measures the concentration of glucose in plasma after 8-12 hours of fasting to screen for or monitor diabetes mellitus.",
                category="laboratory",
                code=code_loinc_fasting_glucose,
                permitted_data_type="quantity",
            )
        )
        cbc_observation_definition = __create_object(
            BaseObservationDefinitionSpec(
                slug="CBC",
                title="Complete Blood Count",
                status="active",
                description="A Complete Blood Count (CBC) is a common laboratory test that evaluates the overall health status by measuring multiple components of blood including red blood cells (RBC), white blood cells (WBC), hemoglobin, hematocrit, and platelets. This test is performed on whole blood using an automated hematology analyzer.",
                category="laboratory",
                code=code_loinc_cbc_panel,
                permitted_data_type="quantity",
                component=[
                    {
                        "code": code_loinc_hemoglobin,
                        "permitted_unit": code_ucum_g_dl,
                        "permitted_data_type": "quantity",
                    },
                    {
                        "code": code_loinc_hematocrit,
                        "permitted_unit": code_ucum_percent,
                        "permitted_data_type": "quantity",
                    },
                    {
                        "code": code_loinc_erythrocytes,
                        "permitted_unit": code_ucum_million_per_ul,
                        "permitted_data_type": "quantity",
                    },
                    {
                        "code": code_loinc_platelets,
                        "permitted_unit": code_ucum_thousands_per_ul,
                        "permitted_data_type": "quantity",
                    },
                ],
                method=code_snomed_automated_count,
                permitted_unit=code_ucum_g_dl,
            )
        )
        lipid_panel_observation_definition = __create_object(
            BaseObservationDefinitionSpec(
                slug="lipid-panel-observation",
                title="Lipid Panel Observation",
                status="active",
                description="A comprehensive blood test measuring cholesterol and triglyceride levels to assess cardiovascular health.",
                category="laboratory",
                code=code_loinc_lipid_panel,
                permitted_data_type="quantity",
            )
        )
        urinalysis_observation_definition = __create_object(
            BaseObservationDefinitionSpec(
                slug="urinalysis-observation",
                title="Urinalysis Observation",
                status="active",
                description="A diagnostic test analyzing urine's physical, chemical, and microscopic properties to detect various conditions.",
                category="laboratory",
                code=code_loinc_urine,
                permitted_data_type="quantity",
                method=code_snomed_urine_dipstick,
            )
        )

        default_price_components = [
            {
                "code": {
                    "code": "oldage",
                    "system": "http://ohc.network/codes/monetary/discount",
                    "display": "Old Age Discount",
                },
                "factor": 10.0,
                "monetary_component_type": "discount",
            },
            {
                "code": {
                    "code": "igst",
                    "system": "http://ohc.network/codes/monetary/tax",
                    "display": "IGST",
                },
                "factor": 6.0,
                "monetary_component_type": "tax",
            },
            {
                "code": {
                    "code": "gst",
                    "system": "http://ohc.network/codes/monetary/tax",
                    "display": "GST",
                },
                "factor": 6.0,
                "monetary_component_type": "tax",
            },
        ]

        fasting_blood_glucose_charge_definition = __create_object(
            ChargeItemDefinitionSpec(
                status="active",
                title="Fasting Blood Glucose Test",
                slug="fasting-blood-glucose-test",
                description="Measures the concentration of glucose in plasma after 8-12 hours of fasting to screen for or monitor diabetes mellitus.",
                purpose="Measures the concentration of glucose in plasma after 8-12 hours of fasting to screen for or monitor diabetes mellitus.",
                price_components=[
                    {"amount": 600.0, "monetary_component_type": "base"},
                    *default_price_components,
                ],
            )
        )
        cbc_charge_definition = __create_object(
            ChargeItemDefinitionSpec(
                status="active",
                title="Complete Blood Count (CBC)",
                slug="complete-blood-count",
                description="A Complete Blood Count (CBC) is a common laboratory test that evaluates the overall health status by measuring multiple components of blood including red blood cells (RBC), white blood cells (WBC), hemoglobin, hematocrit, and platelets. This test is performed on whole blood using an automated hematology analyzer.",
                purpose="A Complete Blood Count (CBC) is a common laboratory test that evaluates the overall health status by measuring multiple components of blood including red blood cells (RBC), white blood cells (WBC), hemoglobin, hematocrit, and platelets. This test is performed on whole blood using an automated hematology analyzer.",
                price_components=[
                    {"amount": 450.0, "monetary_component_type": "base"},
                    {
                        "code": {
                            "code": "child",
                            "system": "http://ohc.network/codes/monetary/discount",
                            "display": "Child Discount",
                        },
                        "factor": 5.0,
                        "monetary_component_type": "discount",
                    },
                    *default_price_components,
                ],
            )
        )
        lipid_panel_charge_definition = __create_object(
            ChargeItemDefinitionSpec(
                status="active",
                title="Lipid Panel Test",
                slug="lipid-panel-test",
                derived_from_uri="urn:chargeitem:lipid-panel",
                description="Comprehensive blood test measuring cholesterol and triglyceride levels to assess cardiovascular health.",
                purpose="Billing for lipid panel diagnostic service.",
                price_components=[
                    {"amount": 400.0, "monetary_component_type": "base"},
                    *default_price_components,
                ],
            )
        )
        urinalysis_charge_definition = __create_object(
            ChargeItemDefinitionSpec(
                status="active",
                title="Urinalysis Test",
                slug="urinalysis-test",
                derived_from_uri="urn:chargeitem:urinalysis",
                description="Diagnostic test analyzing urine's physical, chemical, and microscopic properties to detect various conditions.",
                purpose="Billing for urinalysis diagnostic service.",
                price_components=[
                    {"amount": 500.0, "monetary_component_type": "base"},
                    {"amount": 15.55, "monetary_component_type": "discount"},
                    {
                        "code": {
                            "code": "cgst",
                            "system": "http://ohc.network/codes/monetary/tax",
                            "display": "CGST",
                        },
                        "factor": 3.0,
                        "monetary_component_type": "tax",
                    },
                    *default_price_components,
                ],
                version=1,
            )
        )

        pathology_service = __create_object(
            BaseHealthcareServiceSpec(
                internal_type="lab",
                name="Pathology Lab",
                styling_metadata={"careIcon": "microscope"},
                extra_details="",
            ),
            locations=[bio_chemistry_lab_location.id],
        )

        __create_object(
            BaseActivityDefinitionSpec(
                slug="fasting_glucose",
                title="Fasting Blood Glucose",
                status="active",
                description="Measures the concentration of glucose in plasma after 8-12 hours of fasting to screen for or monitor diabetes mellitus.",
                usage="Measures the concentration of glucose in plasma after 8-12 hours of fasting to screen for or monitor diabetes mellitus.",
                category="laboratory",
                kind="service_request",
                code=code_snomed_fasting_glucose,
                diagnostic_report_codes=[code_loinc_fasting_glucose_serum],
            ),
            specimen_requirements=[blood_glucose_specimen_definition.id],
            observation_result_requirements=[
                fasting_blood_glucose_observation_definition.id
            ],
            locations=[pathology_service.id],
            charge_item_definitions=[fasting_blood_glucose_charge_definition.id],
        )
        __create_object(
            BaseActivityDefinitionSpec(
                id="76c88bae-f4a4-4200-86b9-77f9a26d1a13",
                slug="complete_blood_count",
                title="Complete Blood Count (CBC) Panel",
                status="active",
                description="A Complete Blood Count (CBC) is a common laboratory test that evaluates the overall health status by measuring multiple components of blood including red blood cells (RBC), white blood cells (WBC), hemoglobin, hematocrit, and platelets.",
                usage="test that evaluates the overall health status by measuring multiple components of blood including red blood cells (RBC), ",
                category="laboratory",
                kind="service_request",
                code=code_snomed_cbc,
                diagnostic_report_codes=[code_loinc_cbc_panel],
            ),
            specimen_requirements=[cbc_specimen_definition.id],
            observation_result_requirements=[cbc_observation_definition.id],
            locations=[pathology_service.id],
            charge_item_definitions=[cbc_charge_definition.id],
        )
        __create_object(
            BaseActivityDefinitionSpec(
                slug="lipid_panel",
                title="Lipid Panel",
                status="active",
                derived_from_uri="urn:activity:lipid-panel",
                description="A comprehensive blood test measuring cholesterol and triglyceride levels to assess cardiovascular health.",
                usage="A comprehensive blood test measuring cholesterol and triglyceride levels to assess cardiovascular health.",
                category="laboratory",
                kind="service_request",
                code=code_loinc_lipid_panel,
                diagnostic_report_codes=[code_loinc_lipid_panel],
            ),
            specimen_requirements=[lipid_panel_specimen_definition.id],
            observation_result_requirements=[lipid_panel_observation_definition.id],
            locations=[pathology_service.id],
            charge_item_definitions=[lipid_panel_charge_definition.id],
        )
        __create_object(
            BaseActivityDefinitionSpec(
                slug="urinalysis",
                title="Urinalysis",
                status="active",
                description="A diagnostic test analyzing urine's physical, chemical, and microscopic properties to detect various conditions.",
                usage="A diagnostic test analyzing urine's physical, chemical, and microscopic properties to detect various conditions.",
                category="laboratory",
                kind="service_request",
                code=code_loinc_urine,
                diagnostic_report_codes=[code_loinc_urine],
            ),
            specimen_requirements=[urinalysis_specimen_definition.id],
            observation_result_requirements=[urinalysis_observation_definition.id],
            locations=[pathology_service.id],
            charge_item_definitions=[urinalysis_charge_definition.id],
        )
