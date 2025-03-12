import inspect

from care.emr.models.organization import FacilityOrganizationUser, OrganizationUser
from care.security.models import RolePermission


class PermissionDeniedError(Exception):
    pass


class AuthorizationHandler:
    """
    This is the base class for Authorization Handlers
    Authorization handler must define a list of actions that can be performed and define the methods that
    actually perform the authorization action.

    All Authz methods would be of the signature ( user, obj , **kwargs )
    obj refers to the obj which the user is seeking permission to. obj can also be a string or any datatype as long
    as the logic can handle the type.

    Queries are actions that return a queryset as the response.
    """

    actions = []
    queries = []

    def check_permission_in_organization(self, permissions, user, orgs=None):
        if user.is_superuser:
            return True
        roles = self.get_role_from_permissions(permissions)
        filters = {"role_id__in": roles, "user": user}
        if orgs:
            filters["organization_id__in"] = orgs
        return OrganizationUser.objects.filter(**filters).exists()

    def check_permission_in_facility_organization(
        self, permissions, user, orgs=None, facility=None
    ):
        if user.is_superuser:
            return True

        for perm in permissions:
            roles = self.get_role_from_permissions([perm])
            filters = {"role_id__in": roles, "user": user}
            if orgs is not None:
                filters["organization_id__in"] = orgs
            if facility is not None:
                filters["organization__facility"] = facility

            if not FacilityOrganizationUser.objects.filter(**filters).exists():
                return False

        return True

    def get_role_from_permissions(self, permissions):
        # TODO Cache this endpoint
        return list(
            set(
                RolePermission.objects.filter(
                    permission__slug__in=permissions
                ).values_list("role_id", flat=True)
            )
        )


class AuthorizationController:
    """
    Someone please write this because i honestly forgot what this does
    """

    override_authz_controllers: list[
        AuthorizationHandler
    ] = []  # The order is important
    # Override Security Controllers will be defined from plugs
    internal_authz_controllers: list[AuthorizationHandler] = []

    cache = {"actions": {}, "queries": {}}

    @classmethod
    def build_cache(cls):
        for controller in (
            cls.internal_authz_controllers + cls.override_authz_controllers
        ):
            for method in inspect.getmembers(controller(), predicate=inspect.ismethod):
                if method[0].startswith("can_"):
                    cls.cache["actions"][method[0]] = controller
                if method[0].startswith("get_"):
                    cls.cache["queries"][method[0]] = controller

    @classmethod
    def call(cls, item, *args, **kwargs):
        if not cls.cache["actions"]:
            cls.build_cache()
        if item.startswith("can_"):
            if item in cls.cache["actions"]:
                return getattr(cls.cache["actions"][item](), item)(*args, **kwargs)
            raise ValueError("Invalid Action")
        if item.startswith("get_"):
            if item in cls.cache["queries"]:
                return getattr(cls.cache["queries"][item](), item)(*args, **kwargs)
            raise ValueError("Invalid Query")
        raise ValueError("Invalid Item")

    @classmethod
    def register_internal_controller(cls, controller):
        # TODO : Do some deduplication Logic
        cls.internal_authz_controllers.append(controller)
