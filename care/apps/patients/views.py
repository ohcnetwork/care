from django.db.models import F

from django_filters import rest_framework as filters

from rest_framework import (
    generics as rest_generics,
    mixins as rest_mixins,
    permissions as rest_permissions,
    status as rest_status,
    viewsets as rest_viewsets,
)
from apps.commons import (
    constants as commons_constants,
    pagination as commons_pagination,
)
from apps.patients import (
    constants as patients_constants,
    models as patient_models,
    serializers as patient_serializers,
    filters as patients_filters,
)
from apps.commons import permissions as commons_permissions


class PatientViewSet(
    rest_viewsets.GenericViewSet,
    rest_mixins.ListModelMixin,
    rest_mixins.RetrieveModelMixin,
):

    serializer_class = patient_serializers.PatientListSerializer
    pagination_class = commons_pagination.CustomPagination

    def get_queryset(self):
        queryset = patient_models.Patient.objects.all()
        if (
            self.request.user.user_type
            and self.request.user.user_type == commons_constants.PORTEA
        ):
            queryset = queryset.filter(patient_status=patients_constants.HOME_ISOLATION)
        elif (
            self.request.user.user_type
            and self.request.user.user_type == commons_constants.FACILITY_USER
        ):
            queryset = queryset.filter(
                patientfacility__facility__facilityuser__user=self.request.user
            )
        return queryset.annotate(
            facility_status=F("patientfacility__patient_status__name")
        )


class PatientGroupViewSet(rest_viewsets.ModelViewSet):

    queryset = patient_models.PatientGroup.objects.all()
    serializer_class = patient_serializers.PatientGroupSerializer


class CovidStatusViewSet(rest_viewsets.ModelViewSet):

    queryset = patient_models.CovidStatus.objects.all()
    serializer_class = patient_serializers.CovidStatusSerializer


class ClinicalStatusViewSet(rest_viewsets.ModelViewSet):

    queryset = patient_models.ClinicalStatus.objects.all()
    serializer_class = patient_serializers.ClinicalStatusSerializer


class PatientStatusViewSet(rest_viewsets.ModelViewSet):

    queryset = patient_models.PatientStatus.objects.all()
    serializer_class = patient_serializers.PatientStatusSerializer


class PatientTimeLineViewSet(rest_mixins.ListModelMixin, rest_viewsets.GenericViewSet):
    """
    ViewSet for Patient Timeline List
    """

    serializer_class = patient_serializers.PatientTimeLineSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = patients_filters.PatientTimelineFilter
    pagination_class = commons_pagination.CustomPagination

    def get_queryset(self):
        return patient_models.PatientTimeLine.objects.filter(
            patient_id=self.kwargs.get("patient_id")
        )


class PatientSampleTestViewSet(
    rest_mixins.CreateModelMixin,
    rest_mixins.UpdateModelMixin,
    rest_viewsets.GenericViewSet,
):
    """
    views for create and update patient sample test
    """

    queryset = patient_models.PatientSampleTest.objects.all()
    serializer_class = patient_serializers.PatientSampleTestSerializer
