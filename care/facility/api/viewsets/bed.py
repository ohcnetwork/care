from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters as drf_filters
from rest_framework.decorators import action, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
)
from rest_framework.response import Response
from rest_framework.serializers import Serializer, UUIDField
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.bed import BedSerializer, AssetBedSerializer

from care.facility.models import facility
from care.facility.models.asset import Asset, AssetLocation, AssetTransaction, UserDefaultAssetLocation
from care.facility.models.bed import AssetBed, Bed
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities
from care.utils.queryset.asset_location import get_asset_location_queryset
from care.utils.queryset.facility import get_facility_queryset
from care.utils.filters.choicefilter import inverse_choices, CareChoiceFilter

from rest_framework.permissions import IsAuthenticated

inverse_bed_type = inverse_choices(Bed.BedTypeChoices)


class BedFilter(filters.FilterSet):
    facility = filters.UUIDFilter(field_name="facility__external_id")
    location = filters.UUIDFilter(field_name="location__external_id")
    bed_type = CareChoiceFilter(choice_dict=inverse_bed_type)


class BedViewSet(ListModelMixin, RetrieveModelMixin, CreateModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = Bed.objects.all().select_related("facility", "location").order_by("-created_date")
    serializer_class = BedSerializer
    lookup_field = "external_id"
    filter_backends = (filters.DjangoFilterBackend, drf_filters.SearchFilter)
    permission_classes = [IsAuthenticated]
    search_fields = ["name"]
    filterset_class = BedFilter

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        if user.is_superuser:
            pass
        elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(facility__state=user.state)
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(facility__district=user.district)
        else:
            allowed_facilities = get_accessible_facilities(user)
            queryset = queryset.filter(facility__id__in=allowed_facilities)
        return queryset


class AssetBedViewSet(ListModelMixin, RetrieveModelMixin, CreateModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = AssetBed.objects.all().select_related("asset", "bed").order_by("-created_date")
    serializer_class = AssetBedSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        if user.is_superuser:
            pass
        elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(bed__facility__state=user.state)
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(bed__facility__district=user.district)
        else:
            allowed_facilities = get_accessible_facilities(user)
            queryset = queryset.filter(bed__facility__id__in=allowed_facilities)
        return queryset
