from django.db.models import Q

from care.emr.models.organization import FacilityOrganizationUser, OrganizationUser
from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.authorization.patient import PatientAccess
from care.security.permissions.referral import ReferralPermissions


class ReferralAccess(AuthorizationHandler):
    def check_referral_entity_permission(self, user, availability, permission):
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if availability.entity_type == "external_organization":
            return self.check_permission_in_organization(
                [permission],
                user,
                [
                    availability.external_organization.id,
                    *availability.external_organization.parent_cache,
                ],
            )

        if availability.entity_type == "internal_organization":
            return self.check_permission_in_facility_organization(
                [permission],
                user,
                [
                    availability.internal_organization.id,
                    *availability.internal_organization.parent_cache,
                ],
            )
        if availability.entity_type == "facility":
            return bool(
                availability.facility_id
            ) and self.check_permission_in_facility_organization(
                [permission], user, facility=availability.facility, root=True
            )
        return False

    def check_referral_encounter_permission(self, user, encounter, permission):
        if not user.is_authenticated:
            return False
        orgs = [*encounter.facility_organization_cache]
        if encounter.current_location_id:
            orgs.extend(encounter.current_location.facility_organization_cache)
        return self.check_permission_in_facility_organization(
            [permission], user, orgs=orgs
        )

    def check_referral_origin_permission(
        self, user, encounter, permission, patient=None
    ):
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if encounter is not None:
            return self.check_referral_encounter_permission(user, encounter, permission)
        if patient is None:
            return False
        patient_roles = PatientAccess().find_roles_on_patient(user, patient)
        return bool(
            patient_roles.intersection(self.get_role_from_permissions([permission]))
        )

    def can_manage_referral_availability(self, user, availability):
        return self.check_referral_entity_permission(
            user,
            availability,
            ReferralPermissions.can_manage_referral_availability.name,
        )

    def can_view_referral_availability(self, user, availability):
        if not user.is_authenticated or availability.entity_type == "external":
            return False
        if self.can_manage_referral_availability(user, availability):
            return True
        if availability.status != "active":
            return False
        return availability.is_public or any(
            self.check_referral_entity_permission(user, availability, permission)
            for permission in [
                ReferralPermissions.can_read_referral_availability.name,
                ReferralPermissions.can_submit_referral_availability.name,
            ]
        )

    def can_submit_referral_availability(self, user, availability):
        if not user.is_authenticated or availability.status != "active":
            return False
        return availability.is_public or self.check_referral_entity_permission(
            user,
            availability,
            ReferralPermissions.can_submit_referral_availability.name,
        )

    def can_create_referral(self, user, encounter, availability, patient=None):
        return self.check_referral_origin_permission(
            user, encounter, ReferralPermissions.can_create_referral.name, patient
        ) and self.can_submit_referral_availability(user, availability)

    def can_list_entity_referrals(self, user, availability_context):
        return self.check_referral_entity_permission(
            user, availability_context, ReferralPermissions.can_read_referral.name
        )

    def can_list_encounter_referrals(self, user, encounter):
        return self.check_referral_origin_permission(
            user, encounter, ReferralPermissions.can_read_referral.name
        )

    def can_list_patient_referrals(self, user, patient):
        return self.check_referral_origin_permission(
            user, None, ReferralPermissions.can_read_referral.name, patient
        )

    def can_read_referral(self, user, referral):
        permission = ReferralPermissions.can_read_referral.name
        return self.check_referral_origin_permission(
            user, referral.encounter, permission, referral.patient
        ) or self.check_referral_entity_permission(
            user, referral.availability, permission
        )

    def can_write_referral(self, user, referral):
        permission = ReferralPermissions.can_write_referral.name
        return self.check_referral_origin_permission(
            user, referral.encounter, permission, referral.patient
        ) or self.check_referral_entity_permission(
            user, referral.availability, permission
        )

    def get_accessible_referral_availabilities(self, qs, user, entity_type):
        qs = qs.filter(entity_type=entity_type, status="active")
        if not user.is_authenticated:
            return qs.none()
        if user.is_superuser:
            return qs
        roles = self.get_role_from_permissions(
            [
                ReferralPermissions.can_manage_referral_availability.name,
                ReferralPermissions.can_read_referral_availability.name,
                ReferralPermissions.can_submit_referral_availability.name,
            ]
        )
        if entity_type == "external_organization":
            organization_ids = list(
                OrganizationUser.objects.filter(
                    user=user, role_id__in=roles
                ).values_list("organization_id", flat=True)
            )
            readable = Q(external_organization_id__in=organization_ids) | Q(
                external_organization__parent_cache__overlap=organization_ids
            )
        elif entity_type == "internal_organization":
            organization_ids = list(
                FacilityOrganizationUser.objects.filter(
                    user=user, role_id__in=roles
                ).values_list("organization_id", flat=True)
            )
            readable = Q(internal_organization_id__in=organization_ids) | Q(
                internal_organization__parent_cache__overlap=organization_ids
            )
        elif entity_type == "facility":
            facility_ids = FacilityOrganizationUser.objects.filter(
                user=user, role_id__in=roles, organization__org_type="root"
            ).values_list("organization__facility_id", flat=True)
            readable = Q(facility_id__in=facility_ids)
        else:
            return qs.none()
        return qs.filter(Q(is_public=True) | readable)


AuthorizationController.register_internal_controller(ReferralAccess)
