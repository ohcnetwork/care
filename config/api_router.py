from django.conf import settings
from django.conf.urls import include, url
from rest_framework.routers import DefaultRouter, SimpleRouter
from rest_framework_nested.routers import NestedSimpleRouter

from care.facility.api.viewsets.ambulance import AmbulanceCreateViewSet, AmbulanceViewSet
from care.facility.api.viewsets.facility import FacilityViewSet, AllFacilityViewSet
from care.facility.api.viewsets.facility_capacity import FacilityCapacityViewSet
from care.facility.api.viewsets.hospital_doctor import HospitalDoctorViewSet
from care.facility.api.viewsets.patient import FacilityPatientStatsHistoryViewSet, PatientSearchViewSet, PatientViewSet
from care.facility.api.viewsets.patient_consultation import DailyRoundsViewSet, PatientConsultationViewSet
from care.facility.api.viewsets.patient_sample import PatientSampleViewSet
from care.facility.api.viewsets.inventory import (
    FacilityInventoryItemViewSet,
    FacilityInventoryLogViewSet,
    FacilityInventorySummaryViewSet,
    FacilityInventoryMinQuantityViewSet,
)
from care.facility.api.viewsets.patient_search import PatientScopedSearchViewSet

from care.users.api.viewsets.lsg import DistrictViewSet, LocalBodyViewSet, StateViewSet
from care.users.api.viewsets.users import UserViewSet

from care.facility.summarisation.facility_capacity import FacilityCapacitySummaryViewSet
from care.facility.summarisation.patient_summary import PatientSummaryViewSet
from care.facility.summarisation.tests_summary import TestsSummaryViewSet
from care.facility.summarisation.triage_summary import TriageSummaryViewSet


if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("users", UserViewSet)
router.register("facility", FacilityViewSet)
router.register("getallfacilities", AllFacilityViewSet)

router.register("ambulance/create", AmbulanceCreateViewSet)
router.register("ambulance", AmbulanceViewSet)

router.register("patient/search", PatientSearchViewSet)
router.register("patient", PatientViewSet)
router.register("consultation", PatientConsultationViewSet)

# Local Body / LSG Viewsets
router.register("state", StateViewSet)
router.register("district", DistrictViewSet)
router.register("local_body", LocalBodyViewSet)

# Patient Sample
router.register("test_sample", PatientSampleViewSet)

# Patient Search
router.register("patient_search", PatientScopedSearchViewSet)

# Summarisation
router.register("facility_summary", FacilityCapacitySummaryViewSet, basename="summary-facility")
router.register("patient_summary", PatientSummaryViewSet, basename="summary-patient")
router.register("tests_summary", TestsSummaryViewSet, basename="summary-tests")
router.register("triage_summary", TriageSummaryViewSet, basename="summary-triage")


router.register("items", FacilityInventoryItemViewSet)

# Ref: https://github.com/alanjds/drf-nested-routers
facility_nested_router = NestedSimpleRouter(router, r"facility", lookup="facility")
facility_nested_router.register(r"hospital_doctor", HospitalDoctorViewSet)
facility_nested_router.register(r"capacity", FacilityCapacityViewSet)
facility_nested_router.register(r"patient_stats", FacilityPatientStatsHistoryViewSet)
facility_nested_router.register(r"inventory", FacilityInventoryLogViewSet)
facility_nested_router.register(r"inventorysummary", FacilityInventorySummaryViewSet)
facility_nested_router.register(r"min_quantity", FacilityInventoryMinQuantityViewSet)


patient_nested_router = NestedSimpleRouter(router, r"patient", lookup="patient")
patient_nested_router.register(r"test_sample", PatientSampleViewSet)

consultation_nested_router = NestedSimpleRouter(router, r"consultation", lookup="consultation")
consultation_nested_router.register(r"daily_rounds", DailyRoundsViewSet)

app_name = "api"
urlpatterns = [
    url(r"^", include(router.urls)),
    url(r"^", include(facility_nested_router.urls)),
    url(r"^", include(patient_nested_router.urls)),
    url(r"^", include(consultation_nested_router.urls)),
]
