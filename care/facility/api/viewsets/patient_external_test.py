import csv
import io
from collections import defaultdict

from django_filters import rest_framework as filters
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.patient_external_test import PatientExternalTestSerializer
from care.facility.api.viewsets.mixins.access import UserAccessMixin
from care.facility.models import PatientExternalTest
from care.users.models import User


def prettyerrors(errors):
    pretty_errors = defaultdict(list)
    for attribute in PatientExternalTest.HEADER_CSV_MAPPING.keys():
        if attribute in errors:
            for error in errors.get(attribute, ""):
                pretty_errors[attribute].append(str(error))
    return dict(pretty_errors)


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
    parser_classes = (MultiPartParser, FormParser, JSONParser)

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

    def check_upload_permission(self):
        if (
            self.request.user.is_superuser == True
            or self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
        ):
            return True
        return False

    @action(methods=["POST"], detail=False)
    def upload_csv(self, request, *args, **kwargs):
        if not self.check_upload_permission():
            raise PermissionDenied("Permission to Endpoint Denied")
        if len(request.FILES.keys()) != 1:
            raise ValidationError({"file": "Upload 1 File at a time"})
        csv_file = request.FILES[list(request.FILES.keys())[0]]
        csv_file.seek(0)
        reader = csv.DictReader(io.StringIO(csv_file.read().decode("utf-8-sig")))
        errors = {}
        counter = 0
        for row in reader:
            counter += 1
            object_data = {}
            for attribute in PatientExternalTest.HEADER_CSV_MAPPING:
                object_data[attribute] = row[PatientExternalTest.HEADER_CSV_MAPPING[attribute]]
            serialiser_obj = PatientExternalTestSerializer(data=object_data)
            serialiser_obj.is_valid()
            errors[counter] = prettyerrors(serialiser_obj._errors)
        if list(errors.keys()):
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_202_ACCEPTED)
