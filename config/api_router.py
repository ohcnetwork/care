from django.conf import settings
from django.urls import include, path
from rest_framework.routers import DefaultRouter, SimpleRouter
from rest_framework_nested.routers import NestedSimpleRouter

from care.emr.api.otp_viewsets.login import OTPLoginView
from care.emr.api.otp_viewsets.patient import PatientOTPView
from care.emr.api.otp_viewsets.slot import OTPSlotViewSet
from care.emr.api.viewsets.allergy_intolerance import AllergyIntoleranceViewSet
from care.emr.api.viewsets.batch_request import BatchRequestView
from care.emr.api.viewsets.condition import (
    DiagnosisViewSet,
    SymptomViewSet,
)
from care.emr.api.viewsets.consent import ConsentViewSet
from care.emr.api.viewsets.device import (
    DeviceEncounterHistoryViewSet,
    DeviceLocationHistoryViewSet,
    DeviceServiceHistoryViewSet,
    DeviceViewSet,
)
from care.emr.api.viewsets.encounter import EncounterViewSet
from care.emr.api.viewsets.facility import (
    AllFacilityViewSet,
    FacilitySchedulableUsersViewSet,
    FacilityUsersViewSet,
    FacilityViewSet,
)
from care.emr.api.viewsets.facility_organization import (
    FacilityOrganizationUsersViewSet,
    FacilityOrganizationViewSet,
)
from care.emr.api.viewsets.file_upload import FileUploadViewSet
from care.emr.api.viewsets.location import (
    FacilityLocationEncounterViewSet,
    FacilityLocationViewSet,
)
from care.emr.api.viewsets.medication_administration import (
    MedicationAdministrationViewSet,
)
from care.emr.api.viewsets.medication_request import MedicationRequestViewSet
from care.emr.api.viewsets.medication_statement import MedicationStatementViewSet
from care.emr.api.viewsets.meta_artifact import MetaArtifactViewSet
from care.emr.api.viewsets.mfa_login import MFALoginViewSet
from care.emr.api.viewsets.notes import NoteMessageViewSet, NoteThreadViewSet
from care.emr.api.viewsets.observation import ObservationViewSet
from care.emr.api.viewsets.organization import (
    OrganizationPublicViewSet,
    OrganizationUsersViewSet,
    OrganizationViewSet,
)
from care.emr.api.viewsets.patient import PatientViewSet
from care.emr.api.viewsets.questionnaire import (
    QuestionnaireTagsViewSet,
    QuestionnaireViewSet,
)
from care.emr.api.viewsets.questionnaire_response import QuestionnaireResponseViewSet
from care.emr.api.viewsets.resource_request import (
    ResourceRequestCommentViewSet,
    ResourceRequestViewSet,
)
from care.emr.api.viewsets.scheduling import (
    AvailabilityViewSet,
    ScheduleViewSet,
    SlotViewSet,
)
from care.emr.api.viewsets.scheduling.availability_exceptions import (
    AvailabilityExceptionsViewSet,
)
from care.emr.api.viewsets.scheduling.booking import TokenBookingViewSet
from care.emr.api.viewsets.totp import TOTPViewSet
from care.emr.api.viewsets.user import UserViewSet
from care.emr.api.viewsets.valueset import ValueSetViewSet
from care.security.api.viewsets.permissions import PermissionViewSet
from care.security.api.viewsets.roles import RoleViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet, basename="users")

user_nested_router = NestedSimpleRouter(router, r"users", lookup="users")

router.register("files", FileUploadViewSet, basename="files")
router.register("meta_artifacts", MetaArtifactViewSet, basename="meta_artifacts")

router.register("otp", OTPLoginView, basename="otp-login")

router.register("otp/patient", PatientOTPView, basename="otp-patient")

router.register("otp/slots", OTPSlotViewSet, basename="otp-slots")


router.register("batch_requests", BatchRequestView, basename="batch-requests")


router.register("valueset", ValueSetViewSet, basename="value-set")

router.register("questionnaire", QuestionnaireViewSet, basename="questionnaire")

router.register(
    "questionnaire_tag", QuestionnaireTagsViewSet, basename="questionnaire_tags"
)

router.register("organization", OrganizationViewSet, basename="organization")

router.register(
    "govt/organization", OrganizationPublicViewSet, basename="govt-organization"
)

router.register("role", RoleViewSet, basename="role")

router.register("permission", PermissionViewSet, basename="permission")


router.register("encounter", EncounterViewSet, basename="encounter")

router.register("mfa/totp", TOTPViewSet, basename="mfa-totp")

router.register("mfa", MFALoginViewSet, basename="mfa")

organization_nested_router = NestedSimpleRouter(
    router, r"organization", lookup="organization"
)

organization_nested_router.register(
    "users", OrganizationUsersViewSet, basename="organization-users"
)


router.register("resource", ResourceRequestViewSet, basename="resource-request")
resource_nested_router = NestedSimpleRouter(router, r"resource", lookup="resource")
resource_nested_router.register(
    r"comment", ResourceRequestCommentViewSet, basename="resource-request-comment"
)

router.register("facility", FacilityViewSet, basename="facility")

router.register("getallfacilities", AllFacilityViewSet, basename="getallfacilities")
facility_nested_router = NestedSimpleRouter(router, r"facility", lookup="facility")

facility_nested_router.register(
    r"organizations", FacilityOrganizationViewSet, basename="facility-organization"
)
facility_nested_router.register(
    r"users", FacilityUsersViewSet, basename="facility-users"
)
facility_nested_router.register(
    r"schedulable_users",
    FacilitySchedulableUsersViewSet,
    basename="facility-schedulable-users",
)
facility_organization_nested_router = NestedSimpleRouter(
    facility_nested_router, r"organizations", lookup="facility_organizations"
)

facility_organization_nested_router.register(
    "users", FacilityOrganizationUsersViewSet, basename="facility-organization-users"
)

facility_nested_router.register(r"schedule", ScheduleViewSet, basename="schedule")
schedule_nested_router = NestedSimpleRouter(
    facility_nested_router, r"schedule", lookup="schedule"
)
schedule_nested_router.register(
    r"availability", AvailabilityViewSet, basename="schedule-availability"
)

facility_nested_router.register(r"slots", SlotViewSet, basename="slot")

facility_nested_router.register(
    r"appointments", TokenBookingViewSet, basename="appointments"
)

facility_nested_router.register(
    r"schedule_exceptions",
    AvailabilityExceptionsViewSet,
    basename="schedule-exceptions",
)

facility_nested_router.register(
    r"location",
    FacilityLocationViewSet,
    basename="location",
)

facility_nested_router.register(
    r"device",
    DeviceViewSet,
    basename="device",
)

device_nested_router = NestedSimpleRouter(
    facility_nested_router, r"device", lookup="device"
)

device_nested_router.register(
    r"location_history",
    DeviceLocationHistoryViewSet,
    basename="device_location_history",
)


device_nested_router.register(
    r"encounter_history",
    DeviceEncounterHistoryViewSet,
    basename="device_encounter_history",
)

device_nested_router.register(
    r"service_history",
    DeviceServiceHistoryViewSet,
    basename="device_service_history",
)

facility_location_nested_router = NestedSimpleRouter(
    facility_nested_router, r"location", lookup="location"
)

facility_location_nested_router.register(
    r"association",
    FacilityLocationEncounterViewSet,
    basename="association",
)

router.register("patient", PatientViewSet, basename="patient")
patient_nested_router = NestedSimpleRouter(router, r"patient", lookup="patient")

patient_nested_router.register(
    r"allergy_intolerance", AllergyIntoleranceViewSet, basename="allergy-intolerance"
)

patient_nested_router.register(r"symptom", SymptomViewSet, basename="symptom")
patient_nested_router.register(r"diagnosis", DiagnosisViewSet, basename="diagnosis")

patient_nested_router.register(r"consent", ConsentViewSet, basename="consent")

patient_nested_router.register(
    "observation", ObservationViewSet, basename="observation"
)

patient_nested_router.register(
    "questionnaire_response",
    QuestionnaireResponseViewSet,
    basename="questionnaire-response",
)


patient_nested_router.register(
    r"medication/request",
    MedicationRequestViewSet,
    basename="medication-request",
)
patient_nested_router.register(
    r"medication/statement",
    MedicationStatementViewSet,
    basename="medication-statement",
)
patient_nested_router.register(
    r"medication/administration",
    MedicationAdministrationViewSet,
    basename="medication-administration",
)

patient_nested_router.register(
    r"thread",
    NoteThreadViewSet,
    basename="thread",
)

thread_nested_router = NestedSimpleRouter(
    patient_nested_router, r"thread", lookup="thread"
)

thread_nested_router.register(
    r"note",
    NoteMessageViewSet,
    basename="note",
)

app_name = "api"
urlpatterns = [
    path("", include(router.urls)),
    path("", include(user_nested_router.urls)),
    path("", include(facility_nested_router.urls)),
    path("", include(schedule_nested_router.urls)),
    path("", include(patient_nested_router.urls)),
    path("", include(thread_nested_router.urls)),
    path("", include(resource_nested_router.urls)),
    path("", include(organization_nested_router.urls)),
    path("", include(facility_organization_nested_router.urls)),
    path("", include(facility_location_nested_router.urls)),
    path("", include(device_nested_router.urls)),
]
