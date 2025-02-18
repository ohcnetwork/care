from care.emr.resources.base import EMRResource
from care.security.authorization.encounter import EncounterAccess
from care.security.authorization.facility import FacilityAccess
from care.security.authorization.patient import PatientAccess
from care.security.models import RolePermission


class PermissionsMixin(EMRResource):
    permissions: list[str] = []

    @classmethod
    def perform_extra_user_serialization(cls, mapping, obj, user=None):
        super().perform_extra_user_serialization(mapping, obj, user)
        if user:
            cls.add_permissions(mapping, user, obj)


class PatientPermissionsMixin(PermissionsMixin):
    @classmethod
    def add_permissions(cls, mapping, user, patient):
        patient_access = PatientAccess()
        roles = patient_access.find_roles_on_patient(user, patient)
        mapping["permissions"] = list(
            RolePermission.objects.filter(
                role_id__in=roles, permission__context__in=["PATIENT", "FACILITY"]
            ).values_list("permission__slug", flat=True)
        )


class FacilityPermissionsMixin(PermissionsMixin):
    @classmethod
    def add_permissions(cls, mapping, user, facility):
        facility_access = FacilityAccess()
        roles = facility_access.find_roles_on_facility(user, facility)
        mapping["permissions"] = list(
            RolePermission.objects.filter(
                role_id__in=roles, permission__context__in=["FACILITY"]
            ).values_list("permission__slug", flat=True)
        )


class EncounterPermissionsMixin(PermissionsMixin):
    @classmethod
    def add_permissions(cls, mapping, user, encounter):
        encounter_access = EncounterAccess()
        roles = encounter_access.find_roles_on_encounter(user, encounter)
        mapping["permissions"] = list(
            RolePermission.objects.filter(
                role_id__in=roles, permission__context__in=["ENCOUNTER", "PATIENT"]
            ).values_list("permission__slug", flat=True)
        )
