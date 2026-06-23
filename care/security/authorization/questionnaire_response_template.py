from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.questionnaire_response_template import (
    QuestionnaireResponseTemplatePermissions,
)


class QuestionnaireResponseTemplateAccess(AuthorizationHandler):
    def can_write_questionnaire_response_template(self, user, facility=None):
        """
        Check if the user has permission to write questionnaire response templates in the facility
        """
        if facility:
            return self.check_permission_in_facility_organization(
                [
                    QuestionnaireResponseTemplatePermissions.can_write_questionnaire_response_template.name
                ],
                user,
                facility=facility,
            )
        return self.check_permission_in_organization(
            [
                QuestionnaireResponseTemplatePermissions.can_write_questionnaire_response_template.name
            ],
            user,
        )


AuthorizationController.register_internal_controller(
    QuestionnaireResponseTemplateAccess
)
