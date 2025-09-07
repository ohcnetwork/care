from django.conf import settings
from django.urls import include, path
from rest_framework.routers import DefaultRouter, SimpleRouter
from rest_framework_nested.routers import NestedSimpleRouter

from care.emr.api.otp_viewsets.login import OTPLoginView
from care.emr.api.otp_viewsets.patient import PatientOTPView
from care.emr.api.otp_viewsets.slot import OTPSlotViewSet
from care.emr.api.viewsets.account import AccountViewSet
from care.emr.api.viewsets.activity_definition import ActivityDefinitionViewSet
from care.emr.api.viewsets.allergy_intolerance import AllergyIntoleranceViewSet
from care.emr.api.viewsets.batch_request import BatchRequestView
from care.emr.api.viewsets.charge_item import ChargeItemViewSet
from care.emr.api.viewsets.charge_item_definition import ChargeItemDefinitionViewSet
from care.emr.api.viewsets.condition import DiagnosisViewSet, SymptomViewSet
from care.emr.api.viewsets.consent import ConsentViewSet
from care.emr.api.viewsets.device import (
    DeviceEncounterHistoryViewSet,
    DeviceLocationHistoryViewSet,
    DeviceServiceHistoryViewSet,
    DeviceViewSet,
)
from care.emr.api.viewsets.diagnostic_report import DiagnosticReportViewSet
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
from care.emr.api.viewsets.healthcare_service import HealthcareServiceViewSet
from care.emr.api.viewsets.inventory.inventory_item import InventoryItemViewSet
from care.emr.api.viewsets.inventory.product import ProductViewSet
from care.emr.api.viewsets.inventory.product_knowledge import ProductKnowledgeViewSet
from care.emr.api.viewsets.inventory.supply_delivery import SupplyDeliveryViewSet
from care.emr.api.viewsets.inventory.supply_request import SupplyRequestViewSet
from care.emr.api.viewsets.invoice import InvoiceViewSet
from care.emr.api.viewsets.location import (
    FacilityLocationEncounterViewSet,
    FacilityLocationViewSet,
)
from care.emr.api.viewsets.medication_administration import (
    MedicationAdministrationViewSet,
)
from care.emr.api.viewsets.medication_dispense import MedicationDispenseViewSet
from care.emr.api.viewsets.medication_request import (
    MedicationRequestSummaryViewSet,
    MedicationRequestViewSet,
)
from care.emr.api.viewsets.medication_statement import MedicationStatementViewSet
from care.emr.api.viewsets.meta_artifact import MetaArtifactViewSet
from care.emr.api.viewsets.mfa_login import MFALoginViewSet
from care.emr.api.viewsets.notes import NoteMessageViewSet, NoteThreadViewSet
from care.emr.api.viewsets.observation import ObservationViewSet
from care.emr.api.viewsets.observation_definition import ObservationDefinitionViewSet
from care.emr.api.viewsets.organization import (
    OrganizationPublicViewSet,
    OrganizationUsersViewSet,
    OrganizationViewSet,
)
from care.emr.api.viewsets.patient import PatientViewSet
from care.emr.api.viewsets.patient_identifier import PatientIdentifierConfigViewSet
from care.emr.api.viewsets.payment_reconciliation import PaymentReconciliationViewSet
from care.emr.api.viewsets.questionnaire import (
    QuestionnaireTagsViewSet,
    QuestionnaireViewSet,
)
from care.emr.api.viewsets.questionnaire_response import QuestionnaireResponseViewSet
from care.emr.api.viewsets.resource_category import ResourceCategoryViewSet
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
from care.emr.api.viewsets.scheduling.token import TokenViewSet
from care.emr.api.viewsets.scheduling.token_category import TokenCategoryViewSet
from care.emr.api.viewsets.scheduling.token_queue import TokenQueueViewSet
from care.emr.api.viewsets.scheduling.token_sub_queue import TokenSubQueueViewSet
from care.emr.api.viewsets.service_request import ServiceRequestViewSet
from care.emr.api.viewsets.specimen import SpecimenViewSet
from care.emr.api.viewsets.specimen_definition import SpecimenDefinitionViewSet
from care.emr.api.viewsets.tag_config import TagConfigViewSet
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
router.register("supply_delivery", SupplyDeliveryViewSet, basename="supply_delivery")

router.register("supply_request", SupplyRequestViewSet, basename="supply_request")

router.register("tag_config", TagConfigViewSet, basename="tag_config")


router.register(
    "observation_definition",
    ObservationDefinitionViewSet,
    basename="observation_definition",
)

router.register(
    "product_knowledge",
    ProductKnowledgeViewSet,
    basename="product_knowledge",
)

router.register(
    r"medication/dispense",
    MedicationDispenseViewSet,
    basename="medication-dispense",
)

router.register(
    r"patient_identifier_config",
    PatientIdentifierConfigViewSet,
    basename="patient-identifier-config",
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

facility_nested_router.register(
    r"token/queue", TokenQueueViewSet, basename="token-queue"
)

queue_nested_router = NestedSimpleRouter(
    facility_nested_router, r"token/queue", lookup="token_queue"
)

queue_nested_router.register(r"token", TokenViewSet, basename="queue")

facility_nested_router.register(
    r"token/sub_queue", TokenSubQueueViewSet, basename="token-sub-queue"
)

facility_nested_router.register(
    r"token/category", TokenCategoryViewSet, basename="token-category"
)


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

facility_nested_router.register(
    r"specimen_definition",
    SpecimenDefinitionViewSet,
    basename="specimen_definition",
)

facility_nested_router.register(
    r"healthcare_service",
    HealthcareServiceViewSet,
    basename="healthcare_service",
)


facility_nested_router.register(
    r"activity_definition",
    ActivityDefinitionViewSet,
    basename="activity_definition",
)
facility_nested_router.register(
    r"specimen",
    SpecimenViewSet,
    basename="specimen",
)

facility_nested_router.register(
    r"service_request",
    ServiceRequestViewSet,
    basename="service_request",
)

facility_nested_router.register(
    r"account",
    AccountViewSet,
    basename="account",
)

facility_nested_router.register(
    r"charge_item_definition",
    ChargeItemDefinitionViewSet,
    basename="charge_item_definition",
)

facility_nested_router.register(
    r"resource_category",
    ResourceCategoryViewSet,
    basename="resource_category",
)


facility_nested_router.register(
    r"charge_item",
    ChargeItemViewSet,
    basename="charge_item",
)

facility_nested_router.register(
    r"invoice",
    InvoiceViewSet,
    basename="invoice",
)

facility_nested_router.register(
    r"payment_reconciliation",
    PaymentReconciliationViewSet,
    basename="payment_reconciliation",
)

facility_nested_router.register(
    r"product",
    ProductViewSet,
    basename="product",
)

facility_nested_router.register(
    r"medication_request",
    MedicationRequestSummaryViewSet,
    basename="medication_request",
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

facility_location_nested_router.register(
    r"product",
    InventoryItemViewSet,
    basename="inventory-item",
)

router.register("patient", PatientViewSet, basename="patient")
patient_nested_router = NestedSimpleRouter(router, r"patient", lookup="patient")

patient_nested_router.register(
    r"allergy_intolerance", AllergyIntoleranceViewSet, basename="allergy-intolerance"
)

patient_nested_router.register(r"symptom", SymptomViewSet, basename="symptom")
patient_nested_router.register(r"diagnosis", DiagnosisViewSet, basename="diagnosis")

patient_nested_router.register(
    r"diagnostic_report",
    DiagnosticReportViewSet,
    basename="diagnostic_report",
)

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
    path("", include(queue_nested_router.urls)),
    path("", include(patient_nested_router.urls)),
    path("", include(thread_nested_router.urls)),
    path("", include(resource_nested_router.urls)),
    path("", include(organization_nested_router.urls)),
    path("", include(facility_organization_nested_router.urls)),
    path("", include(facility_location_nested_router.urls)),
    path("", include(device_nested_router.urls)),
]
