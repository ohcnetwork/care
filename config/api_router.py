from django.conf import settings
from django.urls import include, path
from rest_framework.routers import DefaultRouter, SimpleRouter
from rest_framework_nested.routers import NestedSimpleRouter

from care.abdm.api.viewsets.abha import AbhaViewSet
from care.abdm.api.viewsets.health_facility import HealthFacilityViewSet
from care.abdm.api.viewsets.healthid import ABDMHealthIDViewSet
from care.facility.api.viewsets.ambulance import (
    AmbulanceCreateViewSet,
    AmbulanceViewSet,
)
from care.facility.api.viewsets.asset import (
    AssetLocationViewSet,
    AssetPublicQRViewSet,
    AssetPublicViewSet,
    AssetRetrieveConfigViewSet,
    AssetServiceViewSet,
    AssetTransactionViewSet,
    AssetViewSet,
    AvailabilityViewSet,
)
from care.facility.api.viewsets.bed import (
    AssetBedViewSet,
    BedViewSet,
    ConsultationBedViewSet,
    PatientAssetBedViewSet,
)
from care.facility.api.viewsets.consultation_diagnosis import (
    ConsultationDiagnosisViewSet,
)
from care.facility.api.viewsets.daily_round import DailyRoundsViewSet
from care.facility.api.viewsets.events import (
    EventTypeViewSet,
    PatientConsultationEventViewSet,
)
from care.facility.api.viewsets.facility import AllFacilityViewSet, FacilityViewSet
from care.facility.api.viewsets.facility_capacity import FacilityCapacityViewSet
from care.facility.api.viewsets.facility_users import FacilityUserViewSet
from care.facility.api.viewsets.file_upload import FileUploadViewSet
from care.facility.api.viewsets.hospital_doctor import HospitalDoctorViewSet
from care.facility.api.viewsets.icd import ICDViewSet
from care.facility.api.viewsets.inventory import (
    FacilityInventoryItemViewSet,
    FacilityInventoryLogViewSet,
    FacilityInventoryMinQuantityViewSet,
    FacilityInventorySummaryViewSet,
)
from care.facility.api.viewsets.notification import NotificationViewSet
from care.facility.api.viewsets.patient import (
    FacilityDischargedPatientViewSet,
    FacilityPatientStatsHistoryViewSet,
    PatientNotesEditViewSet,
    PatientNotesViewSet,
    PatientSearchViewSet,
    PatientViewSet,
)
from care.facility.api.viewsets.patient_consultation import PatientConsultationViewSet
from care.facility.api.viewsets.patient_external_test import PatientExternalTestViewSet
from care.facility.api.viewsets.patient_investigation import (
    InvestigationGroupViewset,
    InvestigationValueViewSet,
    PatientInvestigationSummaryViewSet,
    PatientInvestigationViewSet,
)
from care.facility.api.viewsets.patient_otp import PatientMobileOTPViewSet
from care.facility.api.viewsets.patient_otp_data import OTPPatientDataViewSet
from care.facility.api.viewsets.patient_sample import PatientSampleViewSet
from care.facility.api.viewsets.prescription import (
    ConsultationPrescriptionViewSet,
    MedibaseViewSet,
    MedicineAdministrationViewSet,
)
from care.facility.api.viewsets.resources import (
    ResourceRequestCommentViewSet,
    ResourceRequestViewSet,
)
from care.facility.api.viewsets.shifting import (
    ShifitngRequestCommentViewSet,
    ShiftingViewSet,
)
from care.facility.api.viewsets.summary import (
    DistrictPatientSummaryViewSet,
    FacilityCapacitySummaryViewSet,
    PatientSummaryViewSet,
    TestsSummaryViewSet,
    TriageSummaryViewSet,
)
from care.hcx.api.viewsets.claim import ClaimViewSet
from care.hcx.api.viewsets.communication import CommunicationViewSet
from care.hcx.api.viewsets.gateway import HcxGatewayViewSet
from care.hcx.api.viewsets.policy import PolicyViewSet
from care.users.api.viewsets.lsg import (
    DistrictViewSet,
    LocalBodyViewSet,
    StateViewSet,
    WardViewSet,
)
from care.users.api.viewsets.skill import SkillViewSet
from care.users.api.viewsets.users import UserViewSet
from care.users.api.viewsets.userskill import UserSkillViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("users", UserViewSet)
user_nested_router = NestedSimpleRouter(router, r"users", lookup="users")
user_nested_router.register("skill", UserSkillViewSet)

router.register("skill", SkillViewSet)

router.register("facility", FacilityViewSet)
router.register("getallfacilities", AllFacilityViewSet)

router.register("files", FileUploadViewSet)

router.register("ambulance/create", AmbulanceCreateViewSet)
router.register("ambulance", AmbulanceViewSet)

router.register("icd", ICDViewSet, basename="icd")

router.register("patient/search", PatientSearchViewSet)

router.register("otp/token", PatientMobileOTPViewSet)

router.register("otp/patient", OTPPatientDataViewSet)

router.register("notification", NotificationViewSet)

router.register("patient", PatientViewSet)
router.register("consultation", PatientConsultationViewSet)

router.register("external_result", PatientExternalTestViewSet)

router.register("bed", BedViewSet)
router.register("assetbed", AssetBedViewSet)
router.register("consultationbed", ConsultationBedViewSet)

# Local Body / LSG Viewsets
router.register("state", StateViewSet)
router.register("district", DistrictViewSet)
router.register("local_body", LocalBodyViewSet)
router.register("ward", WardViewSet)

# Patient Sample
router.register("test_sample", PatientSampleViewSet)

# Summarisation
router.register(
    "facility_summary", FacilityCapacitySummaryViewSet, basename="summary-facility"
)
router.register("patient_summary", PatientSummaryViewSet, basename="summary-patient")
router.register("tests_summary", TestsSummaryViewSet, basename="summary-tests")
router.register("triage_summary", TriageSummaryViewSet, basename="summary-triage")

# District Summary

router.register(
    "district_patient_summary",
    DistrictPatientSummaryViewSet,
    basename="district-summary-patient",
)

router.register("items", FacilityInventoryItemViewSet)
# router.register("burn_rate", FacilityInventoryBurnRateViewSet)

router.register("shift", ShiftingViewSet, basename="patient-shift")

shifting_nested_router = NestedSimpleRouter(router, r"shift", lookup="shift")
shifting_nested_router.register(r"comment", ShifitngRequestCommentViewSet)

router.register("resource", ResourceRequestViewSet, basename="resource-request")

resource_nested_router = NestedSimpleRouter(router, r"resource", lookup="resource")
resource_nested_router.register(r"comment", ResourceRequestCommentViewSet)

router.register("investigation/group", InvestigationGroupViewset)
router.register("investigation", PatientInvestigationViewSet)

# Ref: https://github.com/alanjds/drf-nested-routers
facility_nested_router = NestedSimpleRouter(router, r"facility", lookup="facility")
facility_nested_router.register(r"get_users", FacilityUserViewSet)
facility_nested_router.register(r"hospital_doctor", HospitalDoctorViewSet)
facility_nested_router.register(r"capacity", FacilityCapacityViewSet)
facility_nested_router.register(r"patient_stats", FacilityPatientStatsHistoryViewSet)
facility_nested_router.register(r"inventory", FacilityInventoryLogViewSet)
facility_nested_router.register(r"inventorysummary", FacilityInventorySummaryViewSet)
facility_nested_router.register(r"min_quantity", FacilityInventoryMinQuantityViewSet)
facility_nested_router.register(r"asset_location", AssetLocationViewSet)

facility_location_nested_router = NestedSimpleRouter(
    facility_nested_router, r"asset_location", lookup="asset_location"
)
facility_location_nested_router.register(r"availability", AvailabilityViewSet)

facility_nested_router.register(r"patient_asset_beds", PatientAssetBedViewSet)
facility_nested_router.register(
    r"discharged_patients", FacilityDischargedPatientViewSet
)
# facility_nested_router.register("burn_rate", FacilityInventoryBurnRateViewSet)

router.register("asset", AssetViewSet)
router.register("asset_config", AssetRetrieveConfigViewSet)

asset_nested_router = NestedSimpleRouter(router, r"asset", lookup="asset")
asset_nested_router.register(r"availability", AvailabilityViewSet)
asset_nested_router.register(r"service_records", AssetServiceViewSet)
router.register("asset_transaction", AssetTransactionViewSet)

patient_nested_router = NestedSimpleRouter(router, r"patient", lookup="patient")
patient_nested_router.register(r"test_sample", PatientSampleViewSet)
patient_nested_router.register(r"investigation", PatientInvestigationSummaryViewSet)
patient_nested_router.register(r"notes", PatientNotesViewSet)
patient_notes_nested_router = NestedSimpleRouter(
    patient_nested_router, r"notes", lookup="notes"
)
patient_notes_nested_router.register(r"edits", PatientNotesEditViewSet)
patient_nested_router.register(r"abha", AbhaViewSet)

consultation_nested_router = NestedSimpleRouter(
    router, r"consultation", lookup="consultation"
)
consultation_nested_router.register(r"daily_rounds", DailyRoundsViewSet)
consultation_nested_router.register(r"diagnoses", ConsultationDiagnosisViewSet)
consultation_nested_router.register(r"investigation", InvestigationValueViewSet)
consultation_nested_router.register(r"prescriptions", ConsultationPrescriptionViewSet)
consultation_nested_router.register(
    r"prescription_administration", MedicineAdministrationViewSet
)
consultation_nested_router.register(r"events", PatientConsultationEventViewSet)

router.register("event_types", EventTypeViewSet)

router.register("medibase", MedibaseViewSet, basename="medibase")

# HCX
router.register("hcx/policy", PolicyViewSet)
router.register("hcx/claim", ClaimViewSet)
router.register("hcx/communication", CommunicationViewSet)
router.register("hcx", HcxGatewayViewSet)

# Public endpoints
router.register("public/asset", AssetPublicViewSet)
router.register("public/asset_qr", AssetPublicQRViewSet)

# ABDM endpoints
if settings.ENABLE_ABDM:
    router.register("abdm/healthid", ABDMHealthIDViewSet, basename="abdm-healthid")
router.register(
    "abdm/health_facility", HealthFacilityViewSet, basename="abdm-healthfacility"
)

app_name = "api"
urlpatterns = [
    path("", include(router.urls)),
    path("", include(user_nested_router.urls)),
    path("", include(facility_nested_router.urls)),
    path("", include(facility_location_nested_router.urls)),
    path("", include(asset_nested_router.urls)),
    path("", include(patient_nested_router.urls)),
    path("", include(patient_notes_nested_router.urls)),
    path("", include(consultation_nested_router.urls)),
    path("", include(resource_nested_router.urls)),
    path("", include(shifting_nested_router.urls)),
]
