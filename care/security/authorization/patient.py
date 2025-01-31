from django.db.models import Q

from care.emr.models import Encounter, PatientUser
from care.emr.models.organization import FacilityOrganizationUser, OrganizationUser
from care.emr.resources.encounter.constants import COMPLETED_CHOICES
from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.models import RolePermission
from care.security.permissions.patient import PatientPermissions


class PatientAccess(AuthorizationHandler):
    def find_roles_on_patient(self, user, patient):
        role_ids = set()
        # Through Encounter
        encounters = (
            Encounter.objects.filter(patient=patient)
            .exclude(status__in=COMPLETED_CHOICES)
            .values_list(
                "facility_organization_cache",
                "current_location__facility_organization_cache",
            )
        )
        encounter_set = set()
        for encounter in encounters:
            encounter_set = encounter_set.union(set(encounter[0]))
            # Through Location
            if encounter[1]:
                encounter_set = encounter_set.union(set(encounter[1]))
        # Find roles based on Location and
        roles = FacilityOrganizationUser.objects.filter(
            organization_id__in=encounter_set, user=user
        ).values_list("role_id", flat=True)
        role_ids = role_ids.union(set(roles))
        # Through Organization
        roles = OrganizationUser.objects.filter(
            organization_id__in=patient.organization_cache, user=user
        ).values_list("role_id", flat=True)
        role_ids = role_ids.union(set(roles))
        # Through Direct association
        roles = PatientUser.objects.filter(patient=patient, user=user).values_list(
            "role_id", flat=True
        )
        return role_ids.union(set(roles))

    def can_view_patient_obj(self, user, patient):
        if user.is_superuser:
            return True
        user_roles = self.find_roles_on_patient(user, patient)
        return RolePermission.objects.filter(
            permission__slug__in=[PatientPermissions.can_list_patients.name],
            role__in=user_roles,
        ).exists()

    def can_write_patient_obj(self, user, patient):
        if user.is_superuser:
            return True
        user_roles = self.find_roles_on_patient(user, patient)
        return RolePermission.objects.filter(
            permission__slug__in=[PatientPermissions.can_write_patient.name],
            role__in=user_roles,
        ).exists()

    def can_submit_questionnaire_patient_obj(self, user, patient):
        if user.is_superuser:
            return True
        user_roles = self.find_roles_on_patient(user, patient)
        return RolePermission.objects.filter(
            permission__slug__in=[
                PatientPermissions.can_submit_patient_questionnaire.name
            ],
            role__in=user_roles,
        ).exists()

    def can_create_patient(self, user):
        return self.check_permission_in_facility_organization(
            [PatientPermissions.can_create_patient.name], user
        ) or self.check_permission_in_organization(
            [PatientPermissions.can_create_patient.name], user
        )

    def can_view_clinical_data(self, user, patient):
        if user.is_superuser:
            return True
        user_roles = self.find_roles_on_patient(user, patient)
        return RolePermission.objects.filter(
            permission__slug__in=[PatientPermissions.can_view_clinical_data.name],
            role__in=user_roles,
        ).exists()

    def can_view_patient_questionnaire_responses(self, user, patient):
        if user.is_superuser:
            return True
        user_roles = self.find_roles_on_patient(user, patient)
        return RolePermission.objects.filter(
            permission__slug__in=[
                PatientPermissions.can_view_questionnaire_responses.name
            ],
            role__in=user_roles,
        ).exists()

    def get_filtered_patients(self, qs, user):
        if user.is_superuser:
            return qs
        roles = self.get_role_from_permissions(
            [PatientPermissions.can_list_patients.name]
        )
        organization_ids = list(
            OrganizationUser.objects.filter(user=user, role_id__in=roles).values_list(
                "organization_id", flat=True
            )
        )
        return qs.filter(
            Q(organization_cache__overlap=organization_ids)
            | Q(users_cache__overlap=[user.id])
        )


AuthorizationController.register_internal_controller(PatientAccess)
