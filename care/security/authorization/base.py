from care.security.permissions.base import PermissionController


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

    def check_permission(self, user, obj):
        if not PermissionController.has_permission(user, obj):
            raise PermissionDeniedError

        return PermissionController.has_permission(user, obj)


class AuthorizationController:
    """
    This class abstracts all security related operations in care
    This includes Checking if A has access to resource X,
    Filtering query-sets for list based operations and so on.
    Security Controller implicitly caches all cachable operations and expects it to be invalidated.

    SecurityController maintains a list of override Classes, When present,
    The override classes are invoked first and then the predefined classes.
    The overridden classes can choose to call the next function in the hierarchy if needed.
    """

    override_authz_controllers: list[
        AuthorizationHandler
    ] = []  # The order is important
    # Override Security Controllers will be defined from plugs
    internal_authz_controllers: list[AuthorizationHandler] = []

    cache = {}

    @classmethod
    def build_cache(cls):
        for controller in (
            cls.internal_authz_controllers + cls.override_authz_controllers
        ):
            for action in controller.actions:
                if "actions" not in cls.cache:
                    cls.cache["actions"] = {}
                cls.cache["actions"][action] = [
                    *cls.cache["actions"].get(action, []),
                    controller,
                ]

    @classmethod
    def get_action_controllers(cls, action):
        return cls.cache["actions"].get(action, [])

    @classmethod
    def check_action_permission(cls, action, user, obj):
        """
        TODO: Add Caching and capability to remove cache at both user and obj level
        """
        if not cls.cache:
            cls.build_cache()
        controllers = cls.get_action_controllers(action)
        for controller in controllers:
            permission_fn = getattr(controller, action)
            result, _continue = permission_fn(user, obj)
            if not _continue:
                return result
            if not result:
                return result
        return True

    @classmethod
    def register_internal_controller(cls, controller: AuthorizationHandler):
        # TODO : Do some deduplication Logic
        cls.internal_authz_controllers.append(controller)
