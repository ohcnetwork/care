from django.conf import settings
from django.conf.urls import include, url
from rest_framework.routers import DefaultRouter, SimpleRouter
from rest_framework_nested.routers import NestedSimpleRouter

from care.facility.api.viewsets.ambulance import (
    AmbulanceViewSet,
    AmbulanceCreateViewSet,
)
from care.facility.api.viewsets.facility import FacilityViewSet
from care.facility.api.viewsets.facility_capacity import FacilityCapacityViewSet
from care.facility.api.viewsets.hospital_doctor import HospitalDoctorViewSet
from care.users.api.views import UserViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("users", UserViewSet)
router.register("facility", FacilityViewSet)
router.register("ambulance", AmbulanceViewSet)
router.register("ambulance/create", AmbulanceCreateViewSet)


# Ref: https://github.com/alanjds/drf-nested-routers
facility_nested_router = NestedSimpleRouter(router, r'facility', lookup='facility')
facility_nested_router.register(r'hospital_doctor', HospitalDoctorViewSet)
facility_nested_router.register(r'capacity', FacilityCapacityViewSet)

app_name = "api"
urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^', include(facility_nested_router.urls)),
]
