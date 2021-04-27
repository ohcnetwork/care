from django.conf import settings
from django.conf.urls import include, url
from rest_framework.routers import DefaultRouter, SimpleRouter
from rest_framework_nested.routers import NestedSimpleRouter

from care.facility.api.viewsets.ambulance import AmbulanceCreateViewSet, AmbulanceViewSet
from care.facility.api.viewsets.facility import AllFacilityViewSet, FacilityViewSet
from care.facility.api.viewsets.facility_capacity import FacilityCapacityViewSet
from care.facility.api.viewsets.file_upload import FileUploadViewSet
from care.facility.api.viewsets.hospital_doctor import HospitalDoctorViewSet
from care.facility.api.viewsets.inventory import (
    FacilityInventoryBurnRateViewSet,
    FacilityInventoryItemViewSet,
    FacilityInventoryLogViewSet,
    FacilityInventoryMinQuantityViewSet,
    FacilityInventorySummaryViewSet,
)
from care.facility.api.viewsets.notification import NotificationViewSet
from care.facility.api.viewsets.patient import FacilityPatientStatsHistoryViewSet, PatientSearchViewSet, PatientViewSet
from care.facility.api.viewsets.patient_consultation import DailyRoundsViewSet, PatientConsultationViewSet
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
from care.facility.api.viewsets.shifting import ShiftingViewSet
from care.facility.summarisation.district.patient_summary import DistrictPatientSummaryViewSet
from care.facility.summarisation.facility_capacity import FacilityCapacitySummaryViewSet
from care.facility.summarisation.patient_summary import PatientSummaryViewSet
from care.facility.summarisation.tests_summary import TestsSummaryViewSet
from care.facility.summarisation.triage_summary import TriageSummaryViewSet
from care.users.api.viewsets.lsg import DistrictViewSet, LocalBodyViewSet, StateViewSet, WardViewSet
from care.users.api.viewsets.users import UserViewSet

from care.life.api.viewsets.lifedata import LifeDataViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("life/data", LifeDataViewSet)

router.register("users", UserViewSet)
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
    "district/patient_summary", DistrictPatientSummaryViewSet, basename="district-summary-patient",
)


router.register("items", FacilityInventoryItemViewSet)
router.register("burn_rate", FacilityInventoryBurnRateViewSet)

router.register("shift", ShiftingViewSet, basename="patient-shift")

router.register("investigation/group", InvestigationGroupViewset)
router.register("investigation", PatientInvestigationViewSet)

# Ref: https://github.com/alanjds/drf-nested-routers
facility_nested_router = NestedSimpleRouter(router, r"facility", lookup="facility")
facility_nested_router.register(r"hospital_doctor", HospitalDoctorViewSet)
facility_nested_router.register(r"capacity", FacilityCapacityViewSet)
facility_nested_router.register(r"patient_stats", FacilityPatientStatsHistoryViewSet)
facility_nested_router.register(r"inventory", FacilityInventoryLogViewSet)
facility_nested_router.register(r"inventorysummary", FacilityInventorySummaryViewSet)
facility_nested_router.register(r"min_quantity", FacilityInventoryMinQuantityViewSet)
facility_nested_router.register("burn_rate", FacilityInventoryBurnRateViewSet)


patient_nested_router = NestedSimpleRouter(router, r"patient", lookup="patient")
patient_nested_router.register(r"test_sample", PatientSampleViewSet)
patient_nested_router.register(r"investigation", PatientInvestigationSummaryViewSet)

consultation_nested_router = NestedSimpleRouter(router, r"consultation", lookup="consultation")
consultation_nested_router.register(r"daily_rounds", DailyRoundsViewSet)
consultation_nested_router.register(r"investigation", InvestigationValueViewSet)

app_name = "api"
urlpatterns = [
    url(r"^", include(router.urls)),
    url(r"^", include(facility_nested_router.urls)),
    url(r"^", include(patient_nested_router.urls)),
    url(r"^", include(consultation_nested_router.urls)),
]
