from django.db.models import Q
from django.utils.decorators import method_decorator
from django_filters import CharFilter, FilterSet, NumberFilter
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters
from rest_framework import serializers
from rest_framework.decorators import action, parser_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelReadOnlyViewSet, EMRModelViewSet
from care.emr.models import Organization, SchedulableUserResource
from care.emr.models.organization import FacilityOrganizationUser, OrganizationUser
from care.emr.resources.facility.spec import (
    FacilityCreateSpec,
    FacilityReadSpec,
    FacilityRetrieveSpec,
)
from care.emr.resources.user.spec import UserSpec
from care.facility.models import Facility
from care.security.authorization import AuthorizationController
from care.users.models import User
from care.utils.file_uploads.cover_image import delete_cover_image, upload_cover_image
from care.utils.models.validators import (
    cover_image_validator,
    custom_image_extension_validator,
)


class FacilityImageUploadSerializer(serializers.ModelSerializer):
    cover_image = serializers.ImageField(
        required=True,
        write_only=True,
        validators=[custom_image_extension_validator, cover_image_validator],
    )
    read_cover_image_url = serializers.URLField(read_only=True)

    class Meta:
        model = Facility
        # Check DRYpermissions before updating
        fields = ("cover_image", "read_cover_image_url")

    def save(self, **kwargs):
        facility: Facility = self.instance
        image = self.validated_data["cover_image"]
        facility.cover_image_url = upload_cover_image(
            image,
            str(facility.external_id),
            "cover_images",
            facility.cover_image_url,
        )
        facility.save(update_fields=["cover_image_url"])
        return facility


class GeoOrganizationFilter(filters.UUIDFilter):
    def filter(self, qs, value):
        if value:
            organization = get_object_or_404(Organization, external_id=value)
            return qs.filter(geo_organization_cache__overlap=[organization.id])
        return qs


class FacilityFilters(filters.FilterSet):
    name = CharFilter(field_name="name", lookup_expr="icontains")
    facility_type = NumberFilter(field_name="facility_type")
    organization = GeoOrganizationFilter()
    phone_number = CharFilter(field_name="phone_number", lookup_expr="iexact")


class FacilityViewSet(EMRModelViewSet):
    database_model = Facility
    pydantic_model = FacilityCreateSpec
    pydantic_read_model = FacilityReadSpec
    pydantic_retrieve_model = FacilityRetrieveSpec
    filterset_class = FacilityFilters
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        organization_ids = list(
            OrganizationUser.objects.filter(user=self.request.user).values_list(
                "organization_id", flat=True
            )
        )
        return qs.filter(
            Q(
                id__in=FacilityOrganizationUser.objects.filter(
                    user=self.request.user
                ).values_list("organization__facility_id")
            )
            | Q(geo_organization_cache__overlap=organization_ids)
        )

    def authorize_create(self, instance):
        if not AuthorizationController.call("can_create_facility", self.request.user):
            raise PermissionDenied("You do not have permission to create Facilities")

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_update_facility_obj", self.request.user, model_instance
        ):
            raise PermissionDenied("You do not have permission to create Facilities")

    def authorize_destroy(self, instance):
        if not self.request.user.is_superuser:
            raise PermissionDenied("Only Super Admins can delete Facilities")

    @method_decorator(parser_classes([MultiPartParser]))
    @action(methods=["POST"], detail=True)
    def cover_image(self, request, external_id):
        facility = self.get_object()
        self.authorize_update({}, facility)
        serializer = FacilityImageUploadSerializer(facility, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @cover_image.mapping.delete
    def cover_image_delete(self, *args, **kwargs):
        facility = self.get_object()
        self.authorize_update({}, facility)
        delete_cover_image(facility.cover_image_url, "cover_images")
        facility.cover_image_url = None
        facility.save()
        return Response(status=204)


class FacilitySchedulableUsersViewSet(EMRModelReadOnlyViewSet):
    database_model = User
    pydantic_read_model = UserSpec
    authentication_classes = []
    permission_classes = []

    def get_queryset(self):
        return User.objects.filter(
            id__in=SchedulableUserResource.objects.filter(
                facility__external_id=self.kwargs["facility_external_id"]
            ).values("user_id")
        )


class FacilityUserFilter(FilterSet):
    username = CharFilter(field_name="username", lookup_expr="icontains")


class FacilityUsersViewSet(EMRModelReadOnlyViewSet):
    database_model = User
    pydantic_read_model = UserSpec
    filterset_class = FacilityUserFilter
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        return User.objects.filter(
            id__in=FacilityOrganizationUser.objects.filter(
                organization__facility__external_id=self.kwargs["facility_external_id"]
            ).values("user_id")
        )


class AllFacilityViewSet(EMRModelReadOnlyViewSet):
    permission_classes = ()
    authentication_classes = ()

    database_model = Facility
    pydantic_model = FacilityCreateSpec
    pydantic_read_model = FacilityReadSpec
    pydantic_retrieve_model = FacilityRetrieveSpec
    filterset_class = FacilityFilters
    filter_backends = (filters.DjangoFilterBackend, drf_filters.SearchFilter)
    lookup_field = "external_id"
    search_fields = ["name"]

    def get_queryset(self):
        return Facility.objects.filter(is_public=True).select_related()
