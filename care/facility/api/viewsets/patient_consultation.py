from django.db.models.query_utils import Q
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.patient_consultation import (
    PatientConsultationIDSerializer,
    PatientConsultationSerializer,
)
from care.facility.api.viewsets.mixins.access import AssetUserAccessMixin
from care.facility.models.mixins.permissions.asset import IsAssetUser
from care.facility.models.patient_consultation import PatientConsultation
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities


class PatientConsultationFilter(filters.FilterSet):
    patient = filters.CharFilter(field_name="patient__external_id")
    facility = filters.NumberFilter(field_name="facility_id")


class PatientConsultationViewSet(
    AssetUserAccessMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    lookup_field = "external_id"
    serializer_class = PatientConsultationSerializer
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    queryset = (
        PatientConsultation.objects.all().select_related("facility").order_by("-id")
    )
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = PatientConsultationFilter

    def get_permissions(self):
        if self.action == "patient_from_asset":
            return (IsAssetUser(),)
        return super().get_permissions()

    def get_queryset(self):
        if self.request.user.is_superuser:
            return self.queryset
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            return self.queryset.filter(
                patient__facility__state=self.request.user.state
            )
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            return self.queryset.filter(
                patient__facility__district=self.request.user.district
            )
        allowed_facilities = get_accessible_facilities(self.request.user)
        applied_filters = Q(patient__facility__id__in=allowed_facilities)
        applied_filters |= Q(assigned_to=self.request.user)
        applied_filters |= Q(patient__assigned_to=self.request.user)
        return self.queryset.filter(applied_filters)

    @swagger_auto_schema(
        responses={200: PatientConsultationIDSerializer},
    )
    @action(detail=False, methods=["GET"])
    def patient_from_asset(self, request):
        consultation = (
            PatientConsultation.objects.select_related("patient")
            .order_by("-id")
            .filter(
                current_bed__bed__in=request.user.asset.bed_set.all(),
                patient__is_active=True,
            )
            .only("external_id", "patient__external_id")
            .first()
        )
        if not consultation:
            raise NotFound({"detail": "No consultation found for this asset"})
        return Response(PatientConsultationIDSerializer(consultation).data)
