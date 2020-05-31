from rest_framework.routers import SimpleRouter
from apps.patients import views as patients_views

app_name = "patients"
routers = SimpleRouter()

routers.register("patient-groups", patients_views.PatientGroupViewSet, basename="cluster_group")
routers.register("covid-status", patients_views.CovidStatusViewSet, basename="covids")
routers.register("clinical-status", patients_views.ClinicalStatusViewSet, basename="clinicals")
routers.register("current-status", patients_views.PatientStatusViewSet, basename="patient_status")
routers.register(
    "timeline/(?P<patient_id>\d+)", patients_views.PatientTimeLineViewSet, basename="patient_timeline",
)
routers.register("daily-callers", patients_views.PortieCallingDetailViewSet, basename="daily_caller")
routers.register("sample-tests", patients_views.PatientSampleTestViewSet, basename="sample_test")
routers.register(
    "patient-transfer", patients_views.PatientTransferViewSet, basename="patient_transfer",
)
routers.register("", patients_views.PatientViewSet, basename="patient")

urlpatterns = routers.urls
