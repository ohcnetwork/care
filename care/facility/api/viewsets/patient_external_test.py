from collections import defaultdict

from django.conf import settings
from django_filters import Filter
from django_filters import rest_framework as filters
from django_filters.filters import DateFromToRangeFilter
from djqscsv import render_to_csv_response
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.mixins import (
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.patient_external_test import (
    PatientExternalTestSerializer,
    PatientExternalTestUpdateSerializer,
)
from care.facility.models import PatientExternalTest
from care.users.models import User


def pretty_errors(errors):
    pretty_errors = defaultdict(list)
    for attribute in PatientExternalTest.HEADER_CSV_MAPPING:
        if attribute in errors:
            for error in errors.get(attribute, ""):
                pretty_errors[attribute].append(str(error))
    return dict(pretty_errors)


class MFilter(Filter):
    def filter(self, qs, value):
        if not value:
            return qs
        values = value.split(",")
        _filter = {
            self.field_name + "__in": values,
            self.field_name + "__isnull": False,
        }
        return qs.filter(**_filter)


class PatientExternalTestFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    srf_id = filters.CharFilter(field_name="srf_id", lookup_expr="icontains")
    mobile_number = filters.CharFilter(
        field_name="mobile_number", lookup_expr="icontains"
    )
    wards = MFilter(field_name="ward__id")
    districts = MFilter(field_name="district__id")
    local_bodies = MFilter(field_name="local_body__id")
    sample_collection_date = DateFromToRangeFilter(field_name="sample_collection_date")
    result_date = DateFromToRangeFilter(field_name="result_date")
    created_date = DateFromToRangeFilter(field_name="created_date")


class PatientExternalTestPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.user_type not in (
            User.TYPE_VALUE_MAP["StaffReadOnly"],
            User.TYPE_VALUE_MAP["Staff"],
            User.TYPE_VALUE_MAP["NurseReadOnly"],
            User.TYPE_VALUE_MAP["Nurse"],
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class PatientExternalTestViewSet(
    RetrieveModelMixin,
    ListModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = PatientExternalTestSerializer
    queryset = (
        PatientExternalTest.objects.select_related("ward", "local_body", "district")
        .all()
        .order_by("-id")
    )
    permission_classes = (IsAuthenticated, PatientExternalTestPermission)
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = PatientExternalTestFilter
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            if self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
                queryset = queryset.filter(district__state=self.request.user.state)
            elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
                queryset = queryset.filter(district=self.request.user.district)
            elif self.request.user.user_type >= User.TYPE_VALUE_MAP["LocalBodyAdmin"]:
                queryset = queryset.filter(local_body=self.request.user.local_body)
            elif self.request.user.user_type >= User.TYPE_VALUE_MAP["WardAdmin"]:
                queryset = queryset.filter(
                    ward=self.request.user.ward, ward__isnull=False
                )
            else:
                queryset = queryset.none()
        return queryset

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return PatientExternalTestUpdateSerializer
        return super().get_serializer_class()

    def destroy(self, request, *args, **kwargs):
        if self.request.user.user_type < User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            raise PermissionDenied
        return super().destroy(request, *args, **kwargs)

    def check_upload_permission(self):
        return bool(
            self.request.user.is_superuser is True
            or self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
        )

    def list(self, request, *args, **kwargs):
        if settings.CSV_REQUEST_PARAMETER in request.GET:
            mapping = PatientExternalTest.CSV_MAPPING.copy()
            pretty_mapping = PatientExternalTest.CSV_MAKE_PRETTY.copy()
            queryset = self.filter_queryset(self.get_queryset()).values(*mapping.keys())
            return render_to_csv_response(
                queryset,
                field_header_map=mapping,
                field_serializer_map=pretty_mapping,
            )
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["external_result"])
    @action(methods=["POST"], detail=False)
    def bulk_upsert(self, request, *args, **kwargs):
        if not self.check_upload_permission():
            msg = "Permission to Endpoint Denied"
            raise PermissionDenied(msg)
        if "sample_tests" not in request.data:
            raise ValidationError({"sample_tests": "No Data was provided"})
        if not isinstance(request.data["sample_tests"], list):
            raise ValidationError({"sample_tests": "Data should be provided as a list"})

        # check if the user is from same district
        for data in request.data["sample_tests"]:
            if str(request.user.district) != data["district"]:
                raise ValidationError({"Error": "User must belong to same district"})

        errors = []
        ser_objects = []
        invalid = False
        for sample in request.data["sample_tests"]:
            serializer = PatientExternalTestSerializer(data=sample)
            valid = serializer.is_valid()
            current_error = pretty_errors(serializer._errors)  # noqa: SLF001
            if current_error and (not valid):
                errors.append(current_error)
                invalid = True
            ser_objects.append(serializer)
        if invalid:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        for ser_object in ser_objects:
            ser_object.save()
        return Response(status=status.HTTP_202_ACCEPTED)
