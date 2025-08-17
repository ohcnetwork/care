from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.product_knowledge import ProductKnowledgePermissions


class ProductKnowledgeAccess(AuthorizationHandler):
    def can_list_facility_product_knowledge(self, user, facility):
        """
        Check if the user has permission to view product knowledge in the facility
        """
        return self.check_permission_in_facility_organization(
            [ProductKnowledgePermissions.can_read_product_knowledge.name],
            user,
            facility=facility,
        )

    def can_write_facility_product_knowledge(self, user, facility):
        """
        Check if the user has permission to view product knowledge in the facility
        """
        return self.check_permission_in_facility_organization(
            [ProductKnowledgePermissions.can_write_product_knowledge.name],
            user,
            facility=facility,
            root=True,
        )


AuthorizationController.register_internal_controller(ProductKnowledgeAccess)
