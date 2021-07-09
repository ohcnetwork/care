from django.db.models.query_utils import Q
from django_filters import rest_framework as filters
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.patient_consultation import PatientConsultationSerializer
from care.facility.models.patient_consultation import PatientConsultation
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities


class PatientConsultationFilter(filters.FilterSet):
    patient = filters.CharFilter(field_name="patient__external_id")
    facility = filters.NumberFilter(field_name="facility_id")


class PatientConsultationViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, GenericViewSet
):
    lookup_field = "external_id"
    serializer_class = PatientConsultationSerializer
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    queryset = PatientConsultation.objects.all().select_related("facility").order_by("-id")
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = PatientConsultationFilter

    def get_queryset(self):
        if self.request.user.is_superuser:
            return self.queryset
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            return self.queryset.filter(patient__facility__state=self.request.user.state)
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            return self.queryset.filter(patient__facility__district=self.request.user.district)
        allowed_facilities = get_accessible_facilities(self.request.user)
        applied_filters = Q(patient__facility__id__in=allowed_facilities)
        applied_filters |= Q(assigned_to=self.request.user)
        applied_filters |= Q(patient__assigned_to=self.request.user)
        return self.queryset.filter(applied_filters)

