from django.db.models import Q

from care.emr.models.organization import OrganizationUser
from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.permissions.questionnaire import QuestionnairePermissions


class QuestionnaireAccess(AuthorizationHandler):
    def can_read_questionnaire(self, user, org=None, facility=None):
        if facility:
            return self.check_permission_in_facility_organization(
                [QuestionnairePermissions.can_read_questionnaire.name],
                user,
                facility=facility,
            )
        return self.check_permission_in_organization(
            [QuestionnairePermissions.can_read_questionnaire.name], user, org
        )

    def can_write_questionnaire(self, user, org=None, facility=None):
        if facility:
            return self.check_permission_in_facility_organization(
                [QuestionnairePermissions.can_write_questionnaire.name],
                user,
                orgs=[facility.default_internal_organization_id],
            )
        if org and not isinstance(org, list):
            org = [org]
        return self.check_permission_in_organization(
            [QuestionnairePermissions.can_write_questionnaire.name], user, org
        )

    def can_write_questionnaire_obj(self, user, questionnaire):
        if questionnaire.facility:
            return self.check_permission_in_facility_organization(
                [QuestionnairePermissions.can_write_questionnaire.name],
                user,
                orgs=[questionnaire.facility.default_internal_organization_id],
            )
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

    def get_filtered_questionnaires(self, qs, user, facility=None):
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
        filters = Q(organization_cache__overlap=organization_ids)
        if facility:
            filters |= Q(facility=facility)
        return qs.filter(filters).distinct()


AuthorizationController.register_internal_controller(QuestionnaireAccess)
