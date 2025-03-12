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
        if user and user.is_authenticated:
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
    root_org_permissions: list[str] = []
    child_org_permissions: list[str] = []

    @classmethod
    def add_permissions(cls, mapping, user, facility):
        facility_access = FacilityAccess()
        org_roles = facility_access.find_roles_on_facility_sub_orgs(user, facility)
        root_roles = facility_access.find_roles_on_facility_root(user, facility)
        root_org_permissions = list(
            RolePermission.objects.filter(role_id__in=root_roles).values_list(
                "permission__slug", flat=True
            )
        )
        child_org_permissions = list(
            RolePermission.objects.filter(role_id__in=org_roles)
            .exclude(permission__slug="can_update_facility")
            .values_list("permission__slug", flat=True)
        )
        mapping["root_org_permissions"] = root_org_permissions
        mapping["child_org_permissions"] = child_org_permissions
        mapping["permissions"] = list(
            set(root_org_permissions).union(set(child_org_permissions))
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
