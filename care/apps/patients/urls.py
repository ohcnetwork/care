from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.patients import views as patients_views

app_name = "patients"

routers = SimpleRouter()

routers.register("timeline/(?P<patient_id>\d+)", patients_views.PatientTimeLineViewSet, basename="patient_timeline")

urlpatterns = routers.urls
