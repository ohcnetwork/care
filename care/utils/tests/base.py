import sys
from secrets import choice
from unittest.mock import MagicMock

from faker import Faker
from model_bakery import baker
from rest_framework.test import APITestCase

from care.emr.models.organization import FacilityOrganizationUser, OrganizationUser
from care.emr.resources.encounter.constants import (
    ClassChoices,
    EncounterPriorityChoices,
)

# Global mocking, since the types are loaded when specs load, mocking using patch was not working as the validations were already loaded.
sys.modules["care.emr.utils.valueset_coding_type"].validate_valueset = MagicMock(
    return_value={
        "display": "Test Value",
        "system": "http://test_system.care/test",
        "code": "123",
    }
)


class CareAPITestBase(APITestCase):
    fake = Faker()

    def create_user(self, **kwargs):
        from care.users.models import User

        return baker.make(User, **kwargs)

    def create_user_with_password(self, password, **kwargs):
        user = self.create_user(**kwargs)
        user.set_password(password)
        user.save(update_fields=["password"])
        return user

    def create_super_user(self, **kwargs):
        from care.users.models import User

        return baker.make(User, is_superuser=True, **kwargs)

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

        data = {
            "patient": patient,
            "facility": facility,
            "status": status or StatusChoices.in_progress.value,
            "encounter_class": choice(list(ClassChoices)).value,
            "priority": choice(list(EncounterPriorityChoices)).value,
        }

        data.update(**kwargs)

        encounter = baker.make(
            Encounter,
            **data,
        )
        EncounterOrganization.objects.create(
            encounter=encounter, organization=organization
        )
        return encounter

    def attach_role_organization_user(self, organization, user, role):
        OrganizationUser.objects.create(organization=organization, user=user, role=role)

    def attach_role_facility_organization_user(self, facility_organization, user, role):
        FacilityOrganizationUser.objects.create(
            organization=facility_organization, user=user, role=role
        )
