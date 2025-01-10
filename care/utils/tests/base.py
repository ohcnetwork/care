from faker import Faker
from model_bakery import baker
from rest_framework.test import APITestCase

from care.emr.models.organization import FacilityOrganizationUser, OrganizationUser


class CareAPITestBase(APITestCase):
    fake = Faker()

    def create_user(self, **kwargs):
        from care.users.models import User

        return baker.make(User, **kwargs)

    def create_organization(self, **kwargs):
        from care.emr.models import Organization

        return baker.make(Organization, **kwargs)

    def create_facility_organization(self, facility, **kwargs):
        from care.emr.models import FacilityOrganization

        return baker.make(FacilityOrganization, facility=facility, **kwargs)

    def create_role(self, **kwargs):
        from care.security.models import RoleModel

        if RoleModel.objects.filter(**kwargs).exists():
            return RoleModel.objects.get(**kwargs)
        return baker.make(RoleModel, **kwargs)

    def create_role_with_permissions(self, permissions, role_name=None):
        from care.security.models import PermissionModel, RoleModel, RolePermission

        role = baker.make(RoleModel, name=role_name or self.fake.name())

        for permission in permissions:
            RolePermission.objects.create(
                role=role, permission=baker.make(PermissionModel, slug=permission)
            )
        return role

    def create_patient(self, **kwargs):
        from care.emr.models import Patient

        return baker.make(Patient, **kwargs)

    def create_facility(self, user, **kwargs):
        from care.facility.models.facility import Facility

        return baker.make(Facility, created_by=user, **kwargs)

    def create_encounter(self, patient, facility, organization, status=None, **kwargs):
        from care.emr.models import Encounter
        from care.emr.models.encounter import EncounterOrganization
        from care.emr.resources.encounter.constants import StatusChoices

        encounter = baker.make(
            Encounter,
            patient=patient,
            facility=facility,
            status=status or StatusChoices.in_progress.value,
            **kwargs,
        )
        EncounterOrganization.objects.create(
            encounter=encounter, organization=organization
        )
        return encounter

    def create_symptom(self, encounter, patient, **kwargs):
        from secrets import choice

        from care.emr.models import Condition
        from care.emr.resources.condition.spec import (
            CategoryChoices,
            ClinicalStatusChoices,
            SeverityChoices,
            VerificationStatusChoices,
        )

        clinical_status = kwargs.pop(
            "clinical_status", choice(list(ClinicalStatusChoices)).value
        )
        verification_status = kwargs.pop(
            "verification_status", choice(list(VerificationStatusChoices)).value
        )
        severity = kwargs.pop("severity", choice(list(SeverityChoices)).value)

        return baker.make(
            Condition,
            encounter=encounter,
            patient=patient,
            category=CategoryChoices.problem_list_item.value,
            clinical_status=clinical_status,
            verification_status=verification_status,
            severity=severity,
            **kwargs,
        )

    def generate_data_for_symptom(self, encounter, **kwargs):
        from secrets import choice

        from care.emr.resources.condition.spec import (
            CategoryChoices,
            ClinicalStatusChoices,
            SeverityChoices,
            VerificationStatusChoices,
        )

        clinical_status = kwargs.pop(
            "clinical_status", choice(list(ClinicalStatusChoices)).value
        )
        verification_status = kwargs.pop(
            "verification_status", choice(list(VerificationStatusChoices)).value
        )
        severity = kwargs.pop("severity", choice(list(SeverityChoices)).value)
        code = {
            "display": "Low blood pressure",
            "system": "http://snomed.info/sct",
            "code": "45007003",
        }
        return {
            "encounter": encounter.external_id,
            "category": CategoryChoices.problem_list_item.value,
            "clinical_status": clinical_status,
            "verification_status": verification_status,
            "severity": severity,
            "code": code,
            **kwargs,
        }

    def attach_role_organization_user(self, organization, user, role):
        OrganizationUser.objects.create(organization=organization, user=user, role=role)

    def attach_role_facility_organization_user(self, organization, user, role):
        FacilityOrganizationUser.objects.create(
            organization=organization, user=user, role=role
        )
