from care.emr.models.location import FacilityLocation
from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.diagnostic_report import DiagnosticReportPermissions
from care.security.permissions.service_request import ServiceRequestPermissions
from care.security.permissions.specimen import SpecimenPermissions


class ServiceRequestAccess(AuthorizationHandler):
    def check_permission_in_encounter(self, user, encounter, permission):
        orgs = [*encounter.facility_organization_cache]
        if encounter.current_location:
            orgs.extend(encounter.current_location.facility_organization_cache)
        return self.check_permission_in_facility_organization(
            [permission],
            user,
            orgs=orgs,
        )

    def has_permission_on_service_request(self, user, service_request, permission):
        # Check Access to Encounter
        if self.check_permission_in_encounter(
            user,
            service_request.encounter,
            permission,
        ):
            return True
        # Check Access to Locations in Service Request
        location_caches = FacilityLocation.objects.filter(
            id__in=service_request.locations
        ).values_list("facility_organization_cache", flat=True)
        orgs = []
        for org in location_caches:
            orgs.extend(org)
        return self.check_permission_in_facility_organization(
            [permission],
            user,
            orgs=list(set(orgs)),
        )

    def can_read_service_request(self, user, service_request):
        return self.has_permission_on_service_request(
            user,
            service_request,
            ServiceRequestPermissions.can_read_service_request.name,
        )

    def can_write_service_request(self, user, service_request):
        return self.has_permission_on_service_request(
            user,
            service_request,
            ServiceRequestPermissions.can_write_service_request.name,
        )

    def can_write_specimen(self, user, service_request):
        return self.has_permission_on_service_request(
            user,
            service_request,
            SpecimenPermissions.can_write_specimen.name,
        )

    def can_read_specimen(self, user, service_request):
        return self.has_permission_on_service_request(
            user,
            service_request,
            SpecimenPermissions.can_read_specimen.name,
        )

    def can_write_diagnostic_report(self, user, service_request):
        return self.has_permission_on_service_request(
            user,
            service_request,
            DiagnosticReportPermissions.can_write_diagnostic_report.name,
        )

    def can_read_diagnostic_report(self, user, service_request):
        return self.has_permission_on_service_request(
            user,
            service_request,
            DiagnosticReportPermissions.can_read_diagnostic_report.name,
        )

    def can_list_location_service_request(self, user, location):
        """
        Check if the user has permission to view service requests in the given location
        """

        return self.check_permission_in_facility_organization(
            [ServiceRequestPermissions.can_read_service_request.name],
            user,
            orgs=location.facility_organization_cache,
        )


AuthorizationController.register_internal_controller(ServiceRequestAccess)
