from rest_framework.routers import SimpleRouter

from apps.patients import views as patients_views

routers = SimpleRouter()

routers.register("patient", patients_views.PatientViewSet, basename="patient")

urlpatterns = routers.urls
