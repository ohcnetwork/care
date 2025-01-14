import tempfile

from django.core.validators import validate_email as django_validate_email
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel, field_validator
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.emr.models import (
    Encounter,
    EncounterOrganization,
    FacilityOrganization,
    FileUpload,
    Patient,
)
from care.emr.reports import discharge_summary
from care.emr.resources.encounter.constants import COMPLETED_CHOICES
from care.emr.resources.encounter.spec import (
    EncounterCreateSpec,
    EncounterListSpec,
    EncounterRetrieveSpec,
    EncounterUpdateSpec,
)
from care.emr.resources.facility_organization.spec import FacilityOrganizationReadSpec
from care.emr.resources.file_upload.spec import (
    FileCategoryChoices,
    FileTypeChoices,
    FileUploadRetrieveSpec,
)
from care.emr.tasks.discharge_summary import (
    email_discharge_summary_task,
    generate_discharge_summary_task,
)
from care.facility.models import Facility
from care.security.authorization import AuthorizationController


class LiveFilter(filters.CharFilter):
    def filter(self, qs, value):
        queryset = qs
        if not value:
            return queryset
        if value.lower() == "true":
            queryset = queryset.filter(status__in=COMPLETED_CHOICES)
        elif value.lower() == "false":
            queryset = queryset.exclude(status__in=COMPLETED_CHOICES)
        return queryset


class EncounterFilters(filters.FilterSet):
    facility = filters.UUIDFilter(field_name="facility__external_id")
    status = filters.CharFilter(field_name="status", lookup_expr="iexact")
    encounter_class = filters.CharFilter(
        field_name="encounter_class", lookup_expr="iexact"
    )
    priority = filters.CharFilter(field_name="priority", lookup_expr="iexact")
    external_identifier = filters.CharFilter(
        field_name="external_identifier", lookup_expr="icontains"
    )
    phone_number = filters.CharFilter(
        field_name="patient__phone_number", lookup_expr="icontains"
    )
    name = filters.CharFilter(field_name="patient__name", lookup_expr="icontains")
    live = LiveFilter()


class EncounterViewSet(
    EMRCreateMixin, EMRRetrieveMixin, EMRUpdateMixin, EMRListMixin, EMRBaseViewSet
):
    database_model = Encounter
    pydantic_model = EncounterCreateSpec
    pydantic_update_model = EncounterUpdateSpec
    pydantic_read_model = EncounterListSpec
    pydantic_retrieve_model = EncounterRetrieveSpec
    filterset_class = EncounterFilters
    filter_backends = [filters.DjangoFilterBackend]

    def perform_create(self, instance):
        with transaction.atomic():
            organizations = getattr(instance, "_organizations", [])
            super().perform_create(instance)
            for organization in organizations:
                EncounterOrganization.objects.create(
                    encounter=instance,
                    organization=get_object_or_404(
                        FacilityOrganization,
                        external_id=organization,
                        facility=instance.facility,
                    ),
                )
            if not organizations:
                instance.sync_organization_cache()

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_update_encounter_obj", self.request.user, model_instance
        ):
            raise PermissionDenied("You do not have permission to update encounter")

    def authorize_create(self, instance):
        # Check if encounter create permission exists on Facility Organization
        facility = get_object_or_404(Facility, external_id=instance.facility)
        if not AuthorizationController.call(
            "can_create_encounter_obj", self.request.user, facility
        ):
            raise PermissionDenied("You do not have permission to create encounter")

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("patient", "facility", "appointment")
            .order_by("-created_date")
        )
        if (
            self.action in ["list", "retrieve"]
            and "patient" in self.request.GET
            and self.request.GET["patient"]
        ):
            # If the user has view access to the patient, then encounter view is also granted for that patient
            patient = get_object_or_404(
                Patient, external_id=self.request.GET["patient"]
            )
            if AuthorizationController.call(
                "can_view_patient_obj", self.request.user, patient
            ):
                return qs.filter(patient=patient)
            raise PermissionDenied("User Cannot access patient")

        if (
            self.action in ["list", "retrieve"]
            and "facility" in self.request.GET
            and self.request.GET["facility"]
        ):
            # If the user has view access to the patient, then encounter view is also granted for that patient
            facility = get_object_or_404(
                Facility, external_id=self.request.GET["facility"]
            )
            return AuthorizationController.call(
                "get_filtered_encounters", qs, self.request.user, facility
            )
        if self.action in ["list", "retrieve"]:
            raise PermissionDenied("Cannot access encounters")
        return qs  # Authz Exists separately for update and deletes

    @action(detail=True, methods=["GET"])
    def organizations(self, request, *args, **kwargs):
        instance = self.get_object()
        self.authorize_update({}, instance)
        encounter_organizations = EncounterOrganization.objects.filter(
            encounter=instance
        ).select_related("organization")
        data = [
            FacilityOrganizationReadSpec.serialize(
                encounter_organization.organization
            ).to_json()
            for encounter_organization in encounter_organizations
        ]
        return Response({"results": data})

    class EncounterOrganizationManageSpec(BaseModel):
        organization: UUID4

    @action(detail=True, methods=["POST"])
    def organizations_add(self, request, *args, **kwargs):
        instance = self.get_object()
        self.authorize_update({}, instance)
        request_data = self.EncounterOrganizationManageSpec(**request.data)
        organization = get_object_or_404(
            FacilityOrganization, external_id=request_data.organization
        )
        if organization.facility.id != instance.facility.id:
            raise PermissionDenied("Organization Incompatible with Encounter")
        encounter_organization = EncounterOrganization.objects.filter(
            encounter=instance, organization=organization
        )
        if encounter_organization.exists():
            raise ValidationError("Organization already exists")
        EncounterOrganization.objects.create(
            encounter=instance, organization=organization
        )
        return Response(FacilityOrganizationReadSpec.serialize(organization).to_json())

    @action(detail=True, methods=["DELETE"])
    def organizations_remove(self, request, *args, **kwargs):
        instance = self.get_object()
        self.authorize_update({}, instance)
        request_data = self.EncounterOrganizationManageSpec(**request.data)
        organization = get_object_or_404(
            FacilityOrganization, external_id=request_data.organization
        )
        if organization.facility.id != instance.facility.id:
            raise PermissionDenied("Organization Incompatible with Encounter")
        encounter_organization = EncounterOrganization.objects.filter(
            encounter=instance, organization=organization
        )
        if not encounter_organization.exists():
            raise ValidationError("Organization does not exist")
        EncounterOrganization.objects.filter(
            encounter=instance, organization=organization
        ).delete()
        return Response({}, status=204)

    def _check_discharge_summary_access(self, encounter):
        if not AuthorizationController.call(
            "can_view_clinical_data", self.request.user, encounter.patient
        ):
            raise PermissionDenied("Permission denied to user")

    def _generate_discharge_summary(self, encounter_ext_id: str):
        if current_progress := discharge_summary.get_progress(encounter_ext_id):
            return Response(
                {
                    "detail": (
                        "Discharge Summary is already being generated, "
                        f"current progress {current_progress}%"
                    )
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        discharge_summary.set_lock(encounter_ext_id, 1)
        generate_discharge_summary_task.delay(encounter_ext_id)
        return Response(
            {"detail": "Discharge Summary will be generated shortly"},
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(
        description="Generate a discharge summary",
        responses={
            200: "Success",
        },
        tags=["encounter"],
    )
    @action(detail=True, methods=["POST"])
    def generate_discharge_summary(self, request, *args, **kwargs):
        encounter = self.get_object()
        self._check_discharge_summary_access(encounter)
        return self._generate_discharge_summary(encounter.external_id)

    @extend_schema(
        description="Get the discharge summary",
        responses={200: "Success"},
        tags=["encounter"],
    )
    @action(detail=True, methods=["GET"])
    def preview_discharge_summary(self, request, *args, **kwargs):
        encounter = self.get_object()
        self._check_discharge_summary_access(encounter)
        summary_file = (
            FileUpload.objects.filter(
                file_type=FileTypeChoices.encounter.value,
                file_category=FileCategoryChoices.discharge_summary.value,
                associating_id=encounter.external_id,
                upload_completed=True,
            )
            .order_by("id")
            .last()
        )
        if summary_file:
            return Response(FileUploadRetrieveSpec.serialize(summary_file).to_json())
        return self._generate_discharge_summary(encounter.external_id)

    class EmailDischargeSummarySpec(BaseModel):
        email: str

        @field_validator("email")
        @classmethod
        def validate_email(cls, value):
            django_validate_email(value)
            return value

    @action(detail=True, methods=["POST"])
    def email_discharge_summary(self, request, *args, **kwargs):
        encounter = self.get_object()
        self._check_discharge_summary_access(encounter)
        encounter_ext_id = encounter.external_id
        if existing_progress := discharge_summary.get_progress(encounter_ext_id):
            return Response(
                {
                    "detail": (
                        "Discharge Summary is already being generated, "
                        f"current progress {existing_progress}%"
                    )
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )

        request_data = self.EmailDischargeSummarySpec(**request.data)
        email = request_data.email
        summary_file = (
            FileUpload.objects.filter(
                file_type=FileTypeChoices.encounter.value,
                file_category=FileCategoryChoices.discharge_summary.value,
                associating_id=encounter_ext_id,
                upload_completed=True,
            )
            .order_by("id")
            .last()
        )
        if not summary_file:
            (
                generate_discharge_summary_task.s(encounter_ext_id)
                | email_discharge_summary_task.s(emails=[email])
            ).delay()
        else:
            email_discharge_summary_task.delay(summary_file.id, [email])
        return Response(
            {"detail": "Discharge Summary will be emailed shortly"},
            status=status.HTTP_202_ACCEPTED,
        )


def dev_preview_discharge_summary(request, encounter_id):
    """
    This is a dev only view to preview the discharge summary template
    """
    encounter = get_object_or_404(Encounter, external_id=encounter_id)
    data = discharge_summary.get_discharge_summary_data(encounter)
    data["date"] = timezone.now()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        discharge_summary.generate_discharge_summary_pdf(data, tmp_file)
        tmp_file.seek(0)

        response = HttpResponse(tmp_file, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="discharge_summary.pdf"'

        return response
