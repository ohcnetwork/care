from django_filters import rest_framework as filters
from dry_rest_permissions.generics import DRYPermissions
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.patient_external_test import PatientExternalTestSerializer
from care.facility.api.viewsets.mixins.access import UserAccessMixin
from care.facility.models import PatientExternalTest
from care.users.models import User


class PatientExternalTestFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")


class PatientExternalTestViewSet(
    RetrieveModelMixin, ListModelMixin, GenericViewSet,
):
    serializer_class = PatientExternalTestSerializer
    queryset = PatientExternalTest.objects.select_related("ward", "local_body", "district").all()
    permission_classes = (IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = PatientExternalTestFilter

    def get_queryset(self):
        queryset = self.queryset
        if not self.request.user.is_superuser:
            if self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
                queryset = queryset.filter(district__state=self.request.user.state)
            elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
                queryset = queryset.filter(district=self.request.user.district)
            elif self.request.user.user_type >= User.TYPE_VALUE_MAP["LocalBodyAdmin"]:
                queryset = queryset.filter(local_body=self.request.user.local_body)
            elif self.request.user.user_type >= User.TYPE_VALUE_MAP["WardAdmin"]:
                queryset = queryset.filter(ward=self.request.user.ward, ward__isnull=False)
        return queryset
