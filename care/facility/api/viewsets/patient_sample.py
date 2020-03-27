from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from care.facility.api.mixins import UserAccessMixin
from care.facility.api.serializers.patient_sample import PatientSampleSerializer
from care.facility.models import PatientSample


class PatientSampleFilterSet(filters.FilterSet):
    district = filters.NumberFilter(field_name="facility__district")
    district_name = filters.CharFilter(
        field_name="facility__facilitylocalgovtbody__district__name", lookup_expr="icontains"
    )


class PatientSampleViewSet(UserAccessMixin, viewsets.ModelViewSet):
    serializer_class = PatientSampleSerializer
    queryset = PatientSample.objects.all()
    permission_classes = (IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = PatientSampleFilterSet

    def list(self, request, *args, **kwargs):
        """
        Patient Sample List

        Available Filters
        - district - District ID
        - district_name - District name - case insensitive match
        """
        return super(PatientSampleViewSet, self).list(request, *args, **kwargs)
