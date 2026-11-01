from abc import ABC, abstractmethod
from inspect import isabstract

from django.db.models import Model
from rest_framework.exceptions import PermissionDenied, ValidationError

from care.emr.models.allergy_intolerance import AllergyIntolerance
from care.emr.models.condition import Condition
from care.emr.models.diagnostic_report import DiagnosticReport
from care.emr.models.file_upload import FileUpload
from care.emr.models.immunisation import Immunization
from care.emr.models.observation import Observation
from care.emr.models.questionnaire import QuestionnaireResponse
from care.emr.models.referral import Referral
from care.emr.models.scheduling.booking import TokenBooking
from care.emr.models.service_request import ServiceRequest
from care.emr.models.specimen import Specimen
from care.emr.resources.allergy_intolerance.spec import AllergyIntoleranceReadSpec
from care.emr.resources.base import EMRResource
from care.emr.resources.condition.spec import ConditionReadSpec
from care.emr.resources.diagnostic_report.spec import DiagnosticReportSpecBase
from care.emr.resources.file_upload.spec import FileUploadRetrieveSpec
from care.emr.resources.immunisation.immunization import ImmunizationListSpec
from care.emr.resources.observation.spec import ObservationReadSpec
from care.emr.resources.questionnaire_response.spec import QuestionnaireResponseReadSpec
from care.emr.resources.referral.spec import ReferralReadSpec
from care.emr.resources.scheduling.slot.spec import TokenBookingMinimumReadSpec
from care.emr.resources.service_request.spec import BaseServiceRequestSpec
from care.emr.resources.specimen.spec import BaseSpecimenSpec
from care.security.authorization import AuthorizationController
from care.security.authorization.file_upload import file_authorizer
from care.users.models import User
from care.utils.shortcuts import get_object_or_404


class ResourceReferenceHandler(ABC):
    resource_type: str = ""
    model: type[Model] | None = None
    read_spec: type[EMRResource] | None = None

    def get_object(self, resource_id):
        return get_object_or_404(self.model, external_id=resource_id)

    @abstractmethod
    def can_read(self, user: User, resource: Model) -> bool:
        pass

    def authorize_read(self, user, resource):
        if not self.can_read(user, resource):
            raise PermissionDenied("Permission denied to read this resource")

    def render(self, resource):
        """Render an object after the caller authorizes direct or delegated access."""
        return self.read_spec.serialize(resource).to_json()


class ResourceReferenceRegistry:
    _registry: dict[str, type[ResourceReferenceHandler]] = {}

    @classmethod
    def register(cls, handler_class):
        """Register a handler, replacing any previous handler for its resource type."""
        if not isinstance(handler_class, type) or not issubclass(
            handler_class, ResourceReferenceHandler
        ):
            raise TypeError("Handler must be a subclass of ResourceReferenceHandler")
        if isabstract(handler_class):
            raise TypeError("Handler must implement its authorization policy")
        if (
            not isinstance(handler_class.resource_type, str)
            or not handler_class.resource_type
        ):
            raise ValueError("Resource type is required")
        if handler_class.model is None or handler_class.read_spec is None:
            raise ValueError("Resource model and read specification are required")
        cls._registry[handler_class.resource_type] = handler_class
        return handler_class

    @classmethod
    def get(cls, resource_type):
        handler_class = cls._registry.get(resource_type)
        if handler_class is None:
            raise ValidationError("Unsupported resource type")
        return handler_class


class ClinicalResourceReferenceHandler(ResourceReferenceHandler):
    def can_read(self, user, resource):
        allowed = AuthorizationController.call(
            "can_view_clinical_data", user, resource.patient
        )
        if resource.encounter_id:
            allowed = allowed or AuthorizationController.call(
                "can_view_encounter_clinical_data", user, resource.encounter
            )
        return allowed


@ResourceReferenceRegistry.register
class DiagnosticReportResourceReferenceHandler(ResourceReferenceHandler):
    resource_type = "diagnostic_report"
    model = DiagnosticReport
    read_spec = DiagnosticReportSpecBase

    def can_read(self, user, resource):
        return bool(resource.service_request_id) and AuthorizationController.call(
            "can_read_diagnostic_report", user, resource.service_request
        )


@ResourceReferenceRegistry.register
class ObservationResourceReferenceHandler(ClinicalResourceReferenceHandler):
    resource_type = "observation"
    model = Observation
    read_spec = ObservationReadSpec


@ResourceReferenceRegistry.register
class ConditionResourceReferenceHandler(ClinicalResourceReferenceHandler):
    resource_type = "condition"
    model = Condition
    read_spec = ConditionReadSpec


@ResourceReferenceRegistry.register
class AllergyIntoleranceResourceReferenceHandler(ClinicalResourceReferenceHandler):
    resource_type = "allergy_intolerance"
    model = AllergyIntolerance
    read_spec = AllergyIntoleranceReadSpec


@ResourceReferenceRegistry.register
class ServiceRequestResourceReferenceHandler(ResourceReferenceHandler):
    resource_type = "service_request"
    model = ServiceRequest
    read_spec = BaseServiceRequestSpec

    def can_read(self, user, resource):
        return AuthorizationController.call("can_read_service_request", user, resource)


@ResourceReferenceRegistry.register
class SpecimenResourceReferenceHandler(ResourceReferenceHandler):
    resource_type = "specimen"
    model = Specimen
    read_spec = BaseSpecimenSpec

    def can_read(self, user, resource):
        return bool(resource.service_request_id) and AuthorizationController.call(
            "can_read_specimen", user, resource.service_request
        )


@ResourceReferenceRegistry.register
class QuestionnaireResponseResourceReferenceHandler(ClinicalResourceReferenceHandler):
    resource_type = "questionnaire_response"
    model = QuestionnaireResponse
    read_spec = QuestionnaireResponseReadSpec

    def can_read(self, user, resource):
        if not resource.encounter_id:
            return AuthorizationController.call(
                "can_view_patient_questionnaire_responses", user, resource.patient
            )
        return super().can_read(user, resource)


@ResourceReferenceRegistry.register
class FileUploadResourceReferenceHandler(ResourceReferenceHandler):
    resource_type = "file_upload"
    model = FileUpload
    read_spec = FileUploadRetrieveSpec

    def can_read(self, user, resource):
        file_authorizer(user, resource.file_type, resource.associating_id, "read")
        return True


@ResourceReferenceRegistry.register
class ImmunizationResourceReferenceHandler(ClinicalResourceReferenceHandler):
    resource_type = "immunization"
    model = Immunization
    read_spec = ImmunizationListSpec


@ResourceReferenceRegistry.register
class AppointmentResourceReferenceHandler(ResourceReferenceHandler):
    resource_type = "appointment"
    model = TokenBooking
    read_spec = TokenBookingMinimumReadSpec

    def can_read(self, user, resource):
        return AuthorizationController.call(
            "can_list_booking", resource.token_slot.resource, user
        )


@ResourceReferenceRegistry.register
class ReferralResourceReferenceHandler(ResourceReferenceHandler):
    resource_type = "referral"
    model = Referral
    read_spec = ReferralReadSpec

    def can_read(self, user, resource):
        return AuthorizationController.call("can_read_referral", user, resource)


def get_resource_handler(resource_type):
    return ResourceReferenceRegistry.get(resource_type)()
