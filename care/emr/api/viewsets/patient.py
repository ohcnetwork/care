import datetime

from django_filters import CharFilter, FilterSet
from django_filters.rest_framework import DjangoFilterBackend
from pydantic import UUID4, BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.models import Organization, PatientUser
from care.emr.models.patient import Patient
from care.emr.resources.patient.spec import (
    PatientCreateSpec,
    PatientListSpec,
    PatientPartialSpec,
    PatientRetrieveSpec,
)
from care.emr.resources.user.spec import UserSpec
from care.security.authorization import AuthorizationController
from care.security.models import RoleModel
from care.users.models import User


class PatientFilters(FilterSet):
    name = CharFilter(field_name="name", lookup_expr="icontains")
    phone_number = CharFilter(field_name="phone_number", lookup_expr="iexact")


class PatientViewSet(EMRModelViewSet):
    database_model = Patient
    pydantic_model = PatientCreateSpec
    pydantic_read_model = PatientListSpec
    pydantic_retrieve_model = PatientRetrieveSpec
    filterset_class = PatientFilters
    filter_backends = [DjangoFilterBackend]

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_write_patient_obj", self.request.user, model_instance
        ):
            raise PermissionDenied("Cannot Create Patient")

    def authorize_create(self, request_obj):
        if not AuthorizationController.call("can_create_patient", self.request.user):
            raise PermissionDenied("Cannot Create Patient")

    def authorize_destroy(self, instance):
        if not self.request.user.is_superuser:
            raise PermissionDenied("Cannot delete patient")

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("created_by", "updated_by", "geo_organization")
        )
        if self.action != "list":
            patient = get_object_or_404(
                Patient, external_id=self.kwargs.get("external_id")
            )
            if AuthorizationController.call(
                "can_view_clinical_data", self.request.user, patient
            ):
                return qs.filter(external_id=self.kwargs.get("external_id"))

        if self.request.GET.get("organization"):
            geo_organization = get_object_or_404(
                Organization,
                external_id=self.request.GET["organization"],
            )
            qs = qs.filter(organization_cache__overlap=[geo_organization.id])
        return AuthorizationController.call(
            "get_filtered_patients", qs, self.request.user
        )

    class SearchRequestSpec(BaseModel):
        name: str = ""
        phone_number: str
        date_of_birth: datetime.date | None = None
        year_of_birth: int | None = None

    @action(detail=False, methods=["POST"])
    def search(self, request, *args, **kwargs):
        max_page_size = 200
        request_data = self.SearchRequestSpec(**request.data)
        queryset = Patient.objects.filter(phone_number=request_data.phone_number)
        if request_data.date_of_birth:
            queryset = queryset.filter(date_of_birth=request_data.date_of_birth)
        if request_data.year_of_birth:
            queryset = queryset.filter(year_of_birth=request_data.year_of_birth)
        if request_data.name:
            queryset = (queryset.filter(name__icontains=request_data.name))[
                :max_page_size
            ]
        data = [PatientPartialSpec.serialize(obj).to_json() for obj in queryset]
        return Response({"results": data})

    class SearchRetrieveRequestSpec(BaseModel):
        phone_number: str
        year_of_birth: int
        partial_id: str

    @action(detail=False, methods=["POST"])
    def search_retrieve(self, request, *args, **kwargs):
        request_data = self.SearchRetrieveRequestSpec(**request.data)
        queryset = Patient.objects.filter(phone_number=request_data.phone_number)
        queryset = queryset.filter(year_of_birth=request_data.year_of_birth)
        for patient in queryset:
            if str(patient.external_id)[:5] == request_data.partial_id:
                return Response(PatientRetrieveSpec.serialize(patient).to_json())
        raise PermissionDenied("No valid patients found")

    @action(detail=True, methods=["GET"])
    def get_users(self, request, *args, **kwargs):
        patient = self.get_object()
        patient_users = PatientUser.objects.filter(patient=patient)
        data = [
            UserSpec.serialize(patient_user.user).to_json()
            for patient_user in patient_users
        ]
        return Response({"results": data})

    class PatientUserCreateSpec(BaseModel):
        user: UUID4
        role: UUID4

    @action(detail=True, methods=["POST"])
    def add_user(self, request, *args, **kwargs):
        request_data = self.PatientUserCreateSpec(**self.request.data)
        user = get_object_or_404(User, external_id=request_data.user)
        role = get_object_or_404(RoleModel, external_id=request_data.role)
        patient = self.get_object()
        self.authorize_update({}, patient)
        if PatientUser.objects.filter(user=user, patient=patient).exists():
            raise ValidationError("User already exists")
        PatientUser.objects.create(user=user, patient=patient, role=role)
        return Response(UserSpec.serialize(user).to_json())

    class PatientUserDeleteSpec(BaseModel):
        user: UUID4

    @action(detail=True, methods=["POST"])
    def delete_user(self, request, *args, **kwargs):
        request_data = self.PatientUserDeleteSpec(**self.request.data)
        user = get_object_or_404(User, external_id=request_data.user)
        patient = self.get_object()
        self.authorize_update({}, patient)
        if not PatientUser.objects.filter(user=user, patient=patient).exists():
            raise ValidationError("User does not exist")
        PatientUser.objects.filter(user=user, patient=patient).delete()
        return Response({})
