class OverrideSecurityController:
    """
    Inherit this class and redefine security operations to reconfigure permission management
    """


class InternalSecurityController:
    """
    This class is strictly to be used within care, This class was built to separate logic
    for permission control across different files
    """


class SecurityController:
    """
    This class abstracts all security related operations in care
    This includes Checking if A has access to resource X,
    Filtering query-sets for list based operations and so on.
    Security Controller implicitly caches all cachable operations and expects it to be invalidated.

    SecurityController maintains a list of override Classes, When present,
    The override classes are invoked first and then the predefined classes.
    """

    OVERRIDE_SECURITY_CONTROLLERS = []  # The order is important
    # Override Security Controllers will be defined from plugs
    INTERNAL_SECURITY_CONTROLLERS = []
