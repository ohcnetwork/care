from care.facility.api.viewsets.facility_users import FacilityUserViewSet
from django.conf import settings
from django.conf.urls import include, url
from rest_framework.routers import DefaultRouter, SimpleRouter
from rest_framework_nested.routers import NestedSimpleRouter

from care.facility.api.viewsets.ambulance import AmbulanceCreateViewSet, AmbulanceViewSet
from care.facility.api.viewsets.asset import AssetLocationViewSet, AssetTransactionViewSet, AssetViewSet
from care.facility.api.viewsets.bed import AssetBedViewSet, BedViewSet, ConsultationBedViewSet
from care.facility.api.viewsets.daily_round import DailyRoundsViewSet
from care.facility.api.viewsets.facility import AllFacilityViewSet, FacilityViewSet
from care.facility.api.viewsets.facility_capacity import FacilityCapacityViewSet
from care.facility.api.viewsets.file_upload import FileUploadViewSet
from care.facility.api.viewsets.hospital_doctor import HospitalDoctorViewSet
from care.facility.api.viewsets.inventory import (
    FacilityInventoryItemViewSet,
    FacilityInventoryLogViewSet,
    FacilityInventoryMinQuantityViewSet,
    FacilityInventorySummaryViewSet,
)
from care.facility.api.viewsets.notification import NotificationViewSet
from care.facility.api.viewsets.patient import (
    FacilityPatientStatsHistoryViewSet,
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
from care.facility.api.viewsets.patient_search import PatientScopedSearchViewSet
from care.facility.api.viewsets.prescription_supplier import (
    PrescriptionSupplierConsultationViewSet,
    PrescriptionSupplierViewSet,
)
from care.facility.api.viewsets.resources import ResourceRequestCommentViewSet, ResourceRequestViewSet
from care.facility.api.viewsets.shifting import ShifitngRequestCommentViewSet, ShiftingViewSet
from care.facility.summarisation.district.patient_summary import DistrictPatientSummaryViewSet
from care.facility.summarisation.facility_capacity import FacilityCapacitySummaryViewSet
from care.facility.summarisation.patient_summary import PatientSummaryViewSet
from care.facility.summarisation.tests_summary import TestsSummaryViewSet
from care.facility.summarisation.triage_summary import TriageSummaryViewSet
from care.users.api.viewsets.lsg import DistrictViewSet, LocalBodyViewSet, StateViewSet, WardViewSet
from care.users.api.viewsets.skill import SkillViewSet
from care.users.api.viewsets.users import UserViewSet
from care.users.api.viewsets.userskill import UserSkillViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("users", UserViewSet)
user_nested_rotuer = NestedSimpleRouter(router, r"users", lookup="users")
user_nested_rotuer.register("skill", UserSkillViewSet)

router.register("skill", SkillViewSet)

router.register("facility", FacilityViewSet)
router.register("getallfacilities", AllFacilityViewSet)

router.register("files", FileUploadViewSet)

router.register("ambulance/create", AmbulanceCreateViewSet)
router.register("ambulance", AmbulanceViewSet)

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


router.register("pharmacy/consultation", PrescriptionSupplierConsultationViewSet)
router.register("pharmacy/prescription", PrescriptionSupplierViewSet)

# Local Body / LSG Viewsets
router.register("state", StateViewSet)
router.register("district", DistrictViewSet)
router.register("local_body", LocalBodyViewSet)
router.register("ward", WardViewSet)

# Patient Sample
router.register("test_sample", PatientSampleViewSet)

# Patient Search
router.register("patient_search", PatientScopedSearchViewSet)

# Summarisation
router.register("facility_summary", FacilityCapacitySummaryViewSet, basename="summary-facility")
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
# facility_nested_router.register("burn_rate", FacilityInventoryBurnRateViewSet)

router.register("asset", AssetViewSet)
router.register("asset_transaction", AssetTransactionViewSet)


patient_nested_router = NestedSimpleRouter(router, r"patient", lookup="patient")
patient_nested_router.register(r"test_sample", PatientSampleViewSet)
patient_nested_router.register(r"investigation", PatientInvestigationSummaryViewSet)
patient_nested_router.register(r"notes", PatientNotesViewSet)

consultation_nested_router = NestedSimpleRouter(router, r"consultation", lookup="consultation")
consultation_nested_router.register(r"daily_rounds", DailyRoundsViewSet)
consultation_nested_router.register(r"investigation", InvestigationValueViewSet)

app_name = "api"
urlpatterns = [
    url(r"^", include(router.urls)),
    url(r"^", include(user_nested_rotuer.urls)),
    url(r"^", include(facility_nested_router.urls)),
    url(r"^", include(patient_nested_router.urls)),
    url(r"^", include(consultation_nested_router.urls)),
    url(r"^", include(resource_nested_router.urls)),
    url(r"^", include(shifting_nested_router.urls)),
]


## Importing Celery Tasks

import care.facility.reports.admin_reports
