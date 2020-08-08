from django_filters import rest_framework as filters
from dry_rest_permissions.generics import DRYPermissions
from rest_framework.permissions import IsAuthenticated
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet
from django.db.models.query_utils import Q

from care.facility.api.serializers.prescription_supplier import PrescriptionSupplierConsultationSerializer
from care.facility.models.patient_consultation import DailyRound, PatientConsultation
from care.users.models import User


class PrescriptionSupplierConsultationFilter(filters.FilterSet):
    patient = filters.CharFilter(field_name="patient__external_id")
    patient_name = filters.CharFilter(field_name="patient__name", lookup_expr="icontains")
    facility = filters.NumberFilter(field_name="facility_id")


class PrescriptionSupplierConsultationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    lookup_field = "external_id"
    serializer_class = PrescriptionSupplierConsultationSerializer
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    queryset = PatientConsultation.objects.all().select_related("facility", "patient").order_by("-id")
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = PrescriptionSupplierConsultationFilter

    def get_queryset(self):
        if self.request.user.is_superuser:
            return self.queryset
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            return self.queryset.filter(patient__facility__district=self.request.user.district)
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            return self.queryset.filter(patient__facility__state=self.request.user.state)
        return self.queryset.filter(
            Q(patient__created_by=self.request.user) | Q(facility__users__id__exact=self.request.user.id)
        ).distinct("id")

