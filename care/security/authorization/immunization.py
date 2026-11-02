from care.emr.resources.encounter.constants import COMPLETED_CHOICES
from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.authorization.encounter import EncounterAccess
from care.security.authorization.patient import PatientAccess
from care.security.models import RolePermission
from care.security.permissions.immunization import ImmunizationPermissions


class ImmunizationAccess(AuthorizationHandler):
    def check_permission_on_patient(self, user, patient, permission):
        if user.is_superuser:
            return True
        return RolePermission.objects.filter(
            permission__slug=permission,
            role_id__in=PatientAccess().find_roles_on_patient(user, patient),
        ).exists()

    def can_read_patient_immunization(self, user, patient):
        return self.check_permission_on_patient(
            user, patient, ImmunizationPermissions.can_read_immunization.name
        )

    def can_read_encounter_immunization(self, user, encounter):
        return EncounterAccess().check_permission_in_encounter(
            user, encounter, ImmunizationPermissions.can_read_immunization.name
        )

    def can_write_encounter_immunization(self, user, encounter):
        if encounter.status in COMPLETED_CHOICES:
            return False
        return EncounterAccess().check_permission_in_encounter(
            user, encounter, ImmunizationPermissions.can_write_immunization.name
        )

    def can_read_patient_immunization_recommendation(self, user, patient):
        return self.check_permission_on_patient(
            user,
            patient,
            ImmunizationPermissions.can_read_immunization_recommendation.name,
        )

    def can_write_patient_immunization_recommendation(self, user, patient):
        return self.check_permission_on_patient(
            user,
            patient,
            ImmunizationPermissions.can_write_immunization_recommendation.name,
        )

    def can_read_encounter_immunization_recommendation(self, user, encounter):
        return EncounterAccess().check_permission_in_encounter(
            user,
            encounter,
            ImmunizationPermissions.can_read_immunization_recommendation.name,
        )

    def can_write_encounter_immunization_recommendation(self, user, encounter):
        if encounter.status in COMPLETED_CHOICES:
            return False
        return EncounterAccess().check_permission_in_encounter(
            user,
            encounter,
            ImmunizationPermissions.can_write_immunization_recommendation.name,
        )

    def can_list_facility_immunization_policy(self, user, facility):
        """
        Check if the user has permission to view immunization policies in the facility
        """
        return self.check_permission_in_facility_organization(
            [ImmunizationPermissions.can_read_immunization_policy.name],
            user,
            facility=facility,
        )

    def can_write_facility_immunization_policy(self, user, facility):
        """
        Check if the user has permission to manage immunization policies in the facility
        """
        return self.check_permission_in_facility_organization(
            [ImmunizationPermissions.can_write_immunization_policy.name],
            user,
            facility=facility,
            root=True,
        )


AuthorizationController.register_internal_controller(ImmunizationAccess)
