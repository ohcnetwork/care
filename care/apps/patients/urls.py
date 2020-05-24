from rest_framework.routers import SimpleRouter

from apps.patients import views as patients_views

routers = SimpleRouter()

routers.register(
    "patientgroups", patients_views.PatientGroupViewSet, basename="cluster_group"
)
routers.register("covids", patients_views.CovidStatusViewSet, basename="covids")
routers.register(
    "clinicals", patients_views.ClinicalStatusViewSet, basename="clinicals"
)
routers.register("status", patients_views.StatusViewSet, basename="status")
routers.register("", patients_views.PatientViewSet, basename="patient")

urlpatterns = routers.urls
