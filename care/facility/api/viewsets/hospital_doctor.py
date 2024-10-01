from dry_rest_permissions.generics import DRYPermissions
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated

from care.facility.api.serializers.hospital_doctor import HospitalDoctorSerializer
from care.facility.api.viewsets import FacilityBaseViewset
from care.facility.models import Facility, HospitalDoctors
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities


class HospitalDoctorViewSet(FacilityBaseViewset, ListModelMixin):
    serializer_class = HospitalDoctorSerializer
    queryset = HospitalDoctors.objects.filter(facility__deleted=False)
    permission_classes = (IsAuthenticated, DRYPermissions)

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset.filter(
            facility__external_id=self.kwargs.get("facility_external_id")
        )
        if user.is_superuser:
            pass
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(facility__state=user.state)
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(facility__district=user.district)
        else:
            allowed_facilities = get_accessible_facilities(user)
            queryset = queryset.filter(facility__id__in=allowed_facilities)
        return queryset

    def get_object(self):
        return get_object_or_404(self.get_queryset(), area=self.kwargs.get("pk"))

    def get_facility(self):
        facility_qs = Facility.objects.filter(
            external_id=self.kwargs.get("facility_external_id")
        )
        if not self.request.user.is_superuser:
            facility_qs.filter(users__id__exact=self.request.user.id)
        return get_object_or_404(facility_qs)

    def perform_create(self, serializer):
        serializer.save(facility=self.get_facility())
