from rest_framework.exceptions import PermissionDenied

from care.emr.reports.report_type_registry import ReportTypeRegistry


def report_authorizer(user, report_type: str, associating_id: str, permission: str):
    """
    Authorize user access to a report based on report type and permission.

    Args:
        user: User requesting access
        report_type: Type of report (from ReportTypeRegistry)
        associating_id: UUID of the associated resource
        permission: Either "read" or "write"

    Raises:
        PermissionDenied: If user doesn't have permission
    """
    try:
        config = ReportTypeRegistry.get(report_type)
    except KeyError:
        msg = f"Invalid report type: {report_type}"
        raise PermissionDenied(msg) from KeyError

    authorizer = config.authorizer_class()

    if permission == "read":
        allowed = authorizer.authorize_read(user, associating_id)
    elif permission == "write":
        allowed = authorizer.authorize_write(user, associating_id)
    else:
        msg = f"Invalid permission type: {permission}. Must be 'read' or 'write'"
        raise ValueError(msg)

    if not allowed:
        msg = f"Cannot {permission} report of type {report_type}"
        raise PermissionDenied(msg)


def read_report_authorizer(user, report_type: str, associating_id: str):
    return report_authorizer(user, report_type, associating_id, "read")


def write_report_authorizer(user, report_type: str, associating_id: str):
    return report_authorizer(user, report_type, associating_id, "write")
