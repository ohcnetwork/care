from django_filters import rest_framework as filters
from rest_framework import (
    generics as rest_generics,
    mixins as rest_mixins,
    permissions as rest_permissions,
    status as rest_status,
    viewsets as rest_viewsets,
)
from apps.commons import pagination as commons_pagination
from apps.patients import (
    models as patient_models,
    serializers as patient_serializers,
    filters as patients_filters,
)
from apps.commons import permissions as commons_permissions


class PatientViewSet(rest_viewsets.ModelViewSet):

    queryset = patient_models.Patient.objects.all()
    serializer_class = patient_serializers.PatientSerializer


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
        return patients_models.PatientTimeLine.objects.filter(
            patient_id=self.kwargs.get("patient_id")
        )
