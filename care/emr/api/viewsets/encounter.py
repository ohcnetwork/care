import tempfile

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
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
from care.emr.api.viewsets.device import disassociate_device_from_encounter
from care.emr.api.viewsets.location import close_related_location_from_encounter
from care.emr.models import (
    Encounter,
    EncounterOrganization,
    FacilityOrganization,
    Patient,
)
from care.emr.reports import discharge_summary
from care.emr.resources.encounter.constants import COMPLETED_CHOICES
from care.emr.resources.encounter.spec import (
    EncounterCareTeamMemberWriteSpec,
    EncounterCreateSpec,
    EncounterListSpec,
    EncounterRetrieveSpec,
    EncounterUpdateSpec,
)
from care.emr.resources.facility_organization.spec import FacilityOrganizationReadSpec
from care.emr.tasks.discharge_summary import generate_discharge_summary_task
from care.facility.models import Facility
from care.security.authorization import AuthorizationController
from care.users.models import User


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
    location = filters.UUIDFilter(field_name="current_location__external_id")
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

    def validate_data(self, instance, model_obj=None):
        if model_obj is None:
            if (
                self.database_model.objects.filter(
                    patient__external_id=instance.patient
                )
                .exclude(status__in=COMPLETED_CHOICES)
                .count()
                >= settings.MAX_ACTIVE_ENCOUNTERS_PER_PATIENT
            ):
                error = f"Patient already has maximum number of active encounters ({settings.MAX_ACTIVE_ENCOUNTERS_PER_PATIENT})"
                raise ValidationError(error)

            if not Patient.objects.filter(external_id=instance.patient).exists():
                raise ValidationError("Patient does not exist")

            if not Facility.objects.filter(external_id=instance.facility).exists():
                raise ValidationError("Facility does not exist")

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

    def perform_update(self, instance):
        with transaction.atomic():
            disassociate_device_from_encounter(instance)
            close_related_location_from_encounter(instance)
            super().perform_update(instance)

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
            .select_related(
                "patient",
                "facility",
                "appointment",
                "current_location",
                "created_by",
                "updated_by",
            )
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

    @extend_schema(
        request=EncounterOrganizationManageSpec,
        responses={200: FacilityOrganizationReadSpec},
    )
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

    @extend_schema(
        request=EncounterOrganizationManageSpec,
    )
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
        return Response({})

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
        if not AuthorizationController.call(
            "can_view_clinical_data", self.request.user, encounter.patient
        ):
            raise PermissionDenied("Permission denied to user")
        encounter_ext_id = encounter.external_id
        if current_progress := discharge_summary.get_progress(encounter_ext_id):
            return Response(
                {
                    "detail": (
                        "Discharge Summary is already being generated, "
                        f"current progress {current_progress}%"
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        discharge_summary.set_lock(encounter_ext_id, 1)
        generate_discharge_summary_task.delay(encounter_ext_id)
        return Response(
            {"detail": "Discharge Summary will be generated shortly"},
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(
        request=EncounterCareTeamMemberWriteSpec, responses={200: EncounterRetrieveSpec}
    )
    @action(detail=True, methods=["POST"])
    def set_care_team_members(self, request, *args, **kwargs):
        request_data = EncounterCareTeamMemberWriteSpec(**request.data)
        encounter = self.get_object()
        self.authorize_update({}, encounter)

        members = []
        users = []
        for member in request_data.members:
            user_obj = get_object_or_404(User, external_id=member.user_id)
            if user_obj.id in users:
                raise ValidationError({"user": "repeats are not allowed"})
            users.append(user_obj.id)
            if not AuthorizationController.call(
                "can_view_encounter_obj", request.user, encounter
            ):
                raise PermissionDenied(
                    "Treating doctor does not have permission on encounter"
                )
            members.append(
                {
                    "user_id": user_obj.id,
                    "role": member.role.model_dump(mode="json", exclude_defaults=True),
                }
            )

        encounter.care_team = members
        encounter.save(update_fields=["care_team"])
        return Response({}, status=status.HTTP_200_OK)


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
