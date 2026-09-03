from django.db.models import Q

from care.emr.models.organization import FacilityOrganizationUser, OrganizationUser
from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.permissions.questionnaire import QuestionnairePermissions


class QuestionnaireAccess(AuthorizationHandler):
    def can_access_facility_questionnaire(
        self, user, facility, questionnaire, read_only
    ):
        """
        Permission to access a questionnaire for a specific facility
        """
        if read_only:
            permission = [QuestionnairePermissions.can_read_questionnaire.name]
            return self.check_permission_in_facility_organization(
                permission,
                user,
                facility=facility,
                orgs=questionnaire.internal_organization_cache,
            )
        permission = [QuestionnairePermissions.can_write_questionnaire.name]
        return self.check_permission_in_facility_organization(
            permission, user, facility, root=True
        )

    def can_access_facility_organization_questionnaire(
        self, user, facility_organization, read_only
    ):
        """
        Permission to access a questionnaire for a specific facility
        """
        if read_only:
            permission = [QuestionnairePermissions.can_read_questionnaire.name]
        else:
            permission = [QuestionnairePermissions.can_write_questionnaire.name]
        return self.check_permission_in_facility_organization(
            permission,
            user,
            facility=facility_organization.facility,
            orgs=[*facility_organization.parent_cache, facility_organization.id],
        )

    def can_access_user_questionnaire_in_faciltiy(self, user, facility, read_only):
        """
        Permission to write a questionnaire for a specific facility as a user
        """
        if read_only:
            permission = [QuestionnairePermissions.can_read_questionnaire.name]
        else:
            permission = [QuestionnairePermissions.can_write_questionnaire.name]
        return self.check_permission_in_facility_organization(
            permission,
            user,
            facility=facility,
        )

    def can_read_questionnaire(self, user, org=None):
        return self.check_permission_in_organization(
            [QuestionnairePermissions.can_read_questionnaire.name], user, org
        )

    def can_write_questionnaire(self, user, org=None):
        if org:
            org = [org]
        return self.check_permission_in_organization(
            [QuestionnairePermissions.can_write_questionnaire.name], user, org
        )

    def can_write_questionnaire_obj(self, user, questionnaire):
        return self.check_permission_in_organization(
            [QuestionnairePermissions.can_write_questionnaire.name],
            user,
            questionnaire.organization_cache,
        )

    def can_submit_questionnaire_obj(self, user, questionnaire):
        return self.check_permission_in_organization(
            [QuestionnairePermissions.can_submit_questionnaire.name],
            user,
            questionnaire.organization_cache,
        )

    def get_filtered_questionnaires(self, qs, user):
        if user.is_superuser:
            return qs
        roles = self.get_role_from_permissions(
            [QuestionnairePermissions.can_read_questionnaire.name]
        )
        organization_ids = list(
            OrganizationUser.objects.filter(user=user, role_id__in=roles).values_list(
                "organization_id", flat=True
            )
        )
        facility_organization_ids = list(
            FacilityOrganizationUser.objects.filter(
                user=user, role_id__in=roles
            ).values_list("organization_id", flat=True)
        )
        return qs.filter(
            Q(organization_cache__overlap=organization_ids)
            | Q(internal_organization_cache__overlap=facility_organization_ids)
            | Q(auth_context="user", created_by=user)
        )


AuthorizationController.register_internal_controller(QuestionnaireAccess)
