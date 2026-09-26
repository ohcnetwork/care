from rest_framework.exceptions import PermissionDenied, ValidationError

from care.emr.models.device import Device
from care.emr.models.location import FacilityLocation
from care.emr.resources.questionnaire.spec import SubjectType
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404


def authorize_facilitylocation_questionnaire_submission(location, user):
    return AuthorizationController.call(
        "can_submit_facility_location_questionnaire", user, location
    )


def authorize_device_questionnaire_submission(device, user):
    return AuthorizationController.call("can_submit_device_questionnaire", user, device)


def authorize_facility_questionnaire_submission(facility, user):
    return AuthorizationController.call(
        "can_submit_facility_questionnaire", user, facility
    )


def authorize_facilitylocation_questionnaire_read(location, user):
    return AuthorizationController.call(
        "can_read_facility_location_questionnaire", user, location
    )


def authorize_device_questionnaire_read(device, user):
    return AuthorizationController.call("can_read_device_questionnaire", user, device)


def authorize_facility_questionnaire_read(facility, user):
    return AuthorizationController.call(
        "can_read_facility_questionnaire", user, facility
    )


def authorize_resource_questionnaire_submission(resource_type, resource, user):
    if resource_type == SubjectType.location:
        if not authorize_facilitylocation_questionnaire_submission(resource, user):
            raise PermissionDenied(
                "Permission Denied to submit facility location questionnaire"
            )
    elif resource_type == SubjectType.device:
        if not authorize_device_questionnaire_submission(resource, user):
            raise PermissionDenied("Permission Denied to submit device questionnaire")
    elif resource_type == SubjectType.facility:
        if not authorize_facility_questionnaire_submission(resource, user):
            raise PermissionDenied("Permission Denied to submit facility questionnaire")
    else:
        err = f"Permission Denied to submit {resource_type} questionnaire"
        raise PermissionDenied(err)


def authorize_resource_questionnaire_response_read(resource_type, resource, user):
    if resource_type == SubjectType.location:
        if not authorize_facilitylocation_questionnaire_read(resource, user):
            raise PermissionDenied(
                "Permission Denied to read facility location questionnaire"
            )
    elif resource_type == SubjectType.device:
        if not authorize_device_questionnaire_read(resource, user):
            raise PermissionDenied("Permission Denied to read device questionnaire")
    elif resource_type == SubjectType.facility:
        if not authorize_facility_questionnaire_read(resource, user):
            raise PermissionDenied("Permission Denied to read facility questionnaire")
    else:
        err = f"Permission Denied to read {resource_type} questionnaire"
        raise PermissionDenied(err)


def get_resource_facility(resource_type, resource):
    if resource_type == SubjectType.location:
        return resource.facility
    if resource_type == SubjectType.device:
        return resource.facility
    if resource_type == SubjectType.facility:
        return resource
    err = f"Invalid resource type: {resource_type}"
    raise ValidationError(err)


def get_questionniare_resource(resource_type, resource):
    if resource_type == SubjectType.location:
        return get_object_or_404(FacilityLocation, external_id=resource)
    if resource_type == SubjectType.device:
        return get_object_or_404(Device, external_id=resource)
    if resource_type == SubjectType.facility:
        return get_object_or_404(Facility, external_id=resource)
    err = f"Invalid resource type: {resource_type}"
    raise ValidationError(err)
