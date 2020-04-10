from dry_rest_permissions.generics import DRYPermissions

from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin

from care.facility.api.serializers.hospital_doctor import HospitalDoctorSerializer
from care.facility.api.viewsets import FacilityBaseViewset
from care.facility.models import Facility, HospitalDoctors

from rest_framework.permissions import IsAuthenticated


from care.users.models import User


class HospitalDoctorViewSet(FacilityBaseViewset, ListModelMixin):
    serializer_class = HospitalDoctorSerializer
    queryset = HospitalDoctors.objects.filter(deleted=False)

    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset.filter(facility__id=self.kwargs.get("facility_pk"))
        if user.is_superuser:
            return queryset
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictAdmin"]:
            return queryset.filter(facility__district=user.district)
        return queryset.filter(facility__created_by=user)

    def get_object(self):
        return get_object_or_404(self.get_queryset(), area=self.kwargs.get("pk"))

    def get_facility(self):
        facility_qs = Facility.objects.filter(pk=self.kwargs.get("facility_pk"))
        if not self.request.user.is_superuser:
            facility_qs.filter(created_by=self.request.user)
        return get_object_or_404(facility_qs)

    def perform_create(self, serializer):
        serializer.save(facility=self.get_facility())

    def create(self, request, *args, **kwargs):
        """
        Facility Doctors Create

        /facility/{facility_pk}/hosptial_doctors/{pk}
        `pk` in the API refers to the area type.
        """
        return super(HospitalDoctorViewSet, self).create(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        """
        Facility Doctors List

        /facility/{facility_pk}/hosptial_doctors/{pk}
        `pk` in the API refers to the area type.
        """
        return super(HospitalDoctorViewSet, self).list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
        Facility Doctors Retrieve

        /facility/{facility_pk}/hosptial_doctors/{pk}
        `pk` in the API refers to the area type.
        """
        return super(HospitalDoctorViewSet, self).retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """
        Facility Doctors Updates

        /facility/{facility_pk}/hosptial_doctors/{pk}
        `pk` in the API refers to the area type.
        """
        return super(HospitalDoctorViewSet, self).update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """
        Facility Doctors Updates

        /facility/{facility_pk}/hosptial_doctors/{pk}
        `pk` in the API refers to the area type.
        """
        return super(HospitalDoctorViewSet, self).partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Facility Doctors Delete

        /facility/{facility_pk}/hosptial_doctors/{pk}
        `pk` in the API refers to the area type.
        """
        return super(HospitalDoctorViewSet, self).destroy(request, *args, **kwargs)
