from dry_rest_permissions.generics import DRYPermissions
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated

from care.users.models import User
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.patient_search import PatientScopedSearchSerializer
from care.facility.models import PatientSearch

from django_filters import rest_framework as filters


class PatientSearchFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    phone_number = filters.CharFilter(field_name="phone_number", lookup_expr="icontains")
    is_active = filters.BooleanFilter(field_name="is_active")
    facility = filters.UUIDFilter(field_name="facility__external_id")


class PatientScopedSearchViewSet(ListModelMixin, GenericViewSet):

    serializer_class = PatientScopedSearchSerializer
    queryset = PatientSearch.objects.all()

    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )

    filter_backends = (filters.DjangoFilterBackend,)

    filterset_class = PatientSearchFilter

    def get_queryset(self):
        user = self.request.user
        # queryset = self.queryset.filter(facility__external_id=self.kwargs.get("facility_external_id"))
        queryset = self.queryset.filter(facility__isnull=False)
        if user.is_superuser:
            return self.queryset  # Gets patient without a facility as well
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictAdmin"]:
            return queryset.filter(facility__district=user.district)
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            return queryset.filter(facility__state=user.state)
        return queryset.filter(facility__users__id__exact=user.id)

    def list(self, request, *args, **kwargs):
        return super(PatientScopedSearchViewSet, self).list(request, *args, **kwargs)
