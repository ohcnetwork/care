from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRTagMixin,
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
from care.emr.models.patient import PatientIdentifier, PatientIdentifierConfig
from care.emr.resources.encounter.constants import COMPLETED_CHOICES, StatusChoices
from care.emr.resources.encounter.spec import (
    EncounterCareTeamMemberWriteSpec,
    EncounterCreateSpec,
    EncounterListSpec,
    EncounterRetrieveSpec,
    EncounterUpdateSpec,
)
from care.emr.resources.facility_organization.spec import FacilityOrganizationReadSpec
from care.emr.resources.patient.spec import validate_identifier_config
from care.emr.resources.patient_identifier.default_expression_evaluator import (
    evaluate_patient_default_expression,
)
from care.emr.resources.tag.config_spec import TagResource
from care.emr.tagging.filters import SingleFacilityTagFilter
from care.facility.models import Facility
from care.security.authorization import AuthorizationController
from care.users.models import User
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.shortcuts import get_object_or_404
from care.utils.time_util import care_now


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


class OrganizationUUIDFilter(filters.UUIDFilter):
    def filter(self, qs, value):
        queryset = qs
        if not value:
            return queryset
        organization = get_object_or_404(
            FacilityOrganization.objects.only("id"), external_id=value
        )
        return queryset.filter(facility_organization_cache__overlap=[organization.id])


class CareTeamUserFilter(filters.CharFilter):
    def filter(self, qs, value):
        queryset = qs
        if not value:
            return queryset
        user = get_object_or_404(User.objects.only("id"), username=value)
        return queryset.filter(care_team_users__overlap=[user.id])


class EncounterFilters(filters.FilterSet):
    facility = filters.UUIDFilter(field_name="facility__external_id")
    status = MultiSelectFilter(field_name="status")
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
    patient_filter = filters.UUIDFilter(field_name="patient__external_id")
    name = filters.CharFilter(field_name="patient__name", lookup_expr="icontains")
    location = filters.UUIDFilter(field_name="current_location__external_id")
    created_date = filters.DateTimeFromToRangeFilter(field_name="created_date")
    live = LiveFilter()
    organization = OrganizationUUIDFilter()
    care_team_user = CareTeamUserFilter()


class EncounterViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRTagMixin,
    EMRBaseViewSet,
):
    database_model = Encounter
    pydantic_model = EncounterCreateSpec
    pydantic_update_model = EncounterUpdateSpec
    pydantic_read_model = EncounterListSpec
    pydantic_retrieve_model = EncounterRetrieveSpec
    filterset_class = EncounterFilters

    filter_backends = [
        filters.DjangoFilterBackend,
        OrderingFilter,
        SingleFacilityTagFilter,
    ]
    ordering_fields = ["created_date", "modified_date"]
    resource_type = TagResource.encounter

    def validate_data(self, instance, model_obj=None):
        if model_obj is None:
            if (
                self.database_model.objects.filter(
                    patient__external_id=instance.patient,
                    facility__external_id=instance.facility,
                )
                .exclude(status__in=COMPLETED_CHOICES)
                .count()
                >= settings.MAX_ACTIVE_ENCOUNTERS_PER_PATIENT_IN_FACILITY
            ):
                error = f"Patient already has maximum number of active encounters ({settings.MAX_ACTIVE_ENCOUNTERS_PER_PATIENT_IN_FACILITY}) in the facility"
                raise ValidationError(error)

            if not Patient.objects.filter(external_id=instance.patient).exists():
                raise ValidationError("Patient does not exist")

            if not Facility.objects.filter(external_id=instance.facility).exists():
                raise ValidationError("Facility does not exist")

    def authorize_retrieve(self, model_instance):
        patient = model_instance.patient
        if AuthorizationController.call(
            "can_view_patient_obj", self.request.user, patient
        ):
            return True
        if AuthorizationController.call(
            "can_view_encounter_obj", self.request.user, model_instance
        ):
            return True
        raise PermissionDenied("You do not have permission to view this patient")

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
            if instance.appointment:
                if instance.appointment.associated_encounter_id:
                    raise ValidationError("Encounter already has an associated booking")
                instance.appointment.associated_encounter = instance
                instance.appointment.save(update_fields=["associated_encounter"])

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
            self.action in ["list"]
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
            raise PermissionDenied("User cannot access patient")

        if (
            self.action in ["list"]
            and "facility" in self.request.GET
            and self.request.GET["facility"]
        ):
            facility = get_object_or_404(
                Facility, external_id=self.request.GET["facility"]
            )

            return AuthorizationController.call(
                "get_filtered_encounters", qs, self.request.user, facility
            )
        if self.action in ["list"]:
            raise PermissionDenied("Cannot access encounters")
        return qs  # Authz Exists separately for update and deletes

    @action(detail=True, methods=["POST"])
    def restart(self, request, *args, **kwargs):
        """
        Moves the encounter to from a completed state to an in progress state
        """
        instance = self.get_object()
        if not AuthorizationController.call(
            "can_restart_encounter_obj", self.request.user, instance
        ):
            raise PermissionDenied("You do not have permission to update encounter")

        if instance.status not in COMPLETED_CHOICES:
            raise ValidationError("Encounter is not in a completed state")
        if instance.modified_date < care_now() - timedelta(
            hours=settings.ENCOUNTER_RESTART_TIME_LIMIT_HOURS
        ):
            err = f"Encounter cannot be restarted after {settings.ENCOUNTER_RESTART_TIME_LIMIT_HOURS} hours"
            raise ValidationError(err)
        instance.status = StatusChoices.in_progress.value
        instance.save(update_fields=["status"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["GET"])
    def organizations(self, request, *args, **kwargs):
        """
        Returns organizations associated with the encounter
        """
        instance = self.get_object()
        self.authorize_retrieve(instance)
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

    class EncounterFacilityIdentifierWriteSpec(BaseModel):
        identifier: UUID4
        value: str | None = None
        set_default: bool = False

    @action(detail=True, methods=["POST"])
    def set_facility_idenitifier(self, request, *args, **kwargs):
        request_data = self.EncounterFacilityIdentifierWriteSpec(**request.data)
        encounter = self.get_object()
        self.authorize_update({}, encounter)
        config = get_object_or_404(
            PatientIdentifierConfig,
            external_id=request_data.identifier,
            facility=encounter.facility,
        )
        if config.config.get("auto_maintained"):
            raise ValidationError(
                {"identifier": "Cannot update auto maintained identifier"},
            )
        patient_identifier = PatientIdentifier.objects.filter(
            patient=encounter.patient, config=config, facility=encounter.facility
        ).first()
        if (
            not request_data.value
            and patient_identifier
            and not request_data.set_default
        ):
            patient_identifier.delete()
        if not patient_identifier:
            patient_identifier = PatientIdentifier(
                patient=encounter.patient, config=config, facility=encounter.facility
            )
        if config.config.get("default_value") and request_data.set_default:
            patient_identifier.value = evaluate_patient_default_expression(
                config, config.config.get("default_value")
            )
        elif request_data.value:
            try:
                validate_identifier_config(
                    {"config": config.config, "config_obj": config},
                    request_data.value,
                    encounter.patient,
                )
            except ValueError as e:
                raise ValidationError({"value": str(e)}) from e

        patient_identifier.value = request_data.value
        patient_identifier.save()
        return Response({})

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
        encounter.save(update_fields=["care_team", "care_team_users"])
        return Response({}, status=status.HTTP_200_OK)
