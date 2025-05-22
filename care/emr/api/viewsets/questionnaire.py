from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.models import (
    Encounter,
    Organization,
    Patient,
    Questionnaire,
    QuestionnaireOrganization,
    QuestionnaireTag,
)
from care.emr.models.organization import FacilityOrganization
from care.emr.models.questionnaire import (
    QuestionnaireFacilityOrganization,
    QuestionnaireResponse,
)
from care.emr.resources.facility_organization.spec import FacilityOrganizationReadSpec
from care.emr.resources.organization.spec import OrganizationReadSpec
from care.emr.resources.questionnaire.spec import (
    QuestionnaireReadSpec,
    QuestionnaireSpec,
    QuestionnaireTagSpec,
    QuestionnaireUpdateSpec,
)
from care.emr.resources.questionnaire.utils import handle_response
from care.emr.resources.questionnaire_response.spec import (
    QuestionnaireResponseReadSpec,
    QuestionnaireSubmitRequest,
)
from care.facility.models.facility import Facility
from care.security.authorization import AuthorizationController


class QuestionnaireTagFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    slug = filters.CharFilter(field_name="slug", lookup_expr="iexact")


class QuestionnaireTagsViewSet(EMRModelViewSet):
    database_model = QuestionnaireTag
    pydantic_model = QuestionnaireTagSpec
    lookup_field = "slug"
    filterset_class = QuestionnaireTagFilter
    filter_backends = [filters.DjangoFilterBackend]

    # TODO : Handle cascades in delete

    def permissions_controller(self, request):
        if self.action in ["list", "retrieve"]:
            return True
        if self.action in ["create", "update", "delete"]:
            return request.user.is_superuser
        return False


class QuestionnaireTagSlugFilter(filters.CharFilter):
    def filter(self, qs, value):
        queryset = qs
        if not value:
            return queryset
        tag = get_object_or_404(QuestionnaireTag, slug=value).id
        return queryset.filter(tags__overlap=[tag])


class QuestionnaireFilter(filters.FilterSet):
    title = filters.CharFilter(field_name="title", lookup_expr="icontains")
    subject_type = filters.CharFilter(field_name="subject_type", lookup_expr="iexact")
    tag_slug = QuestionnaireTagSlugFilter(field_name="tag_slug")
    status = filters.CharFilter(field_name="status", lookup_expr="iexact")


class QuestionnaireViewSet(EMRModelViewSet):
    database_model = Questionnaire
    pydantic_model = QuestionnaireSpec
    pydantic_read_model = QuestionnaireReadSpec
    pydantic_update_model = QuestionnaireUpdateSpec
    lookup_field = "slug"
    filterset_class = QuestionnaireFilter
    filter_backends = [filters.DjangoFilterBackend]

    def get_facility_object(self):
        """
        Get the facility object from the request query params
        """
        facility = self.request.query_params.get("facility")
        if not facility:
            return None
        return get_object_or_404(Facility, external_id=facility)

    def permissions_controller(self, request):
        facility = self.get_facility_object()
        if self.action in ["list", "retrieve", "get_organizations"]:
            return AuthorizationController.call(
                "can_read_questionnaire", request.user, facility=facility
            )
        if self.action in ["create", "set_organizations", "set_tags"]:
            return AuthorizationController.call(
                "can_write_questionnaire", request.user, facility=facility
            )

        return request.user.is_authenticated

    def authorize_update(self, request_obj, model_instance):
        if self.request.user.is_superuser:
            return True
        if model_instance.facility and AuthorizationController.call(
            "can_write_questionnaire_obj",
            self.request.user,
            questionnaire=model_instance,
        ):
            return True
        raise PermissionDenied(
            "You do not have permission to update this questionnaire"
        )

    def authorize_destroy(self, instance):
        self.authorize_update(self.request, instance)

        if QuestionnaireResponse.objects.filter(questionnaire=instance).exists():
            raise ValidationError("Cannot delete a questionnaire with responses")

    def perform_create(self, instance):
        with transaction.atomic():
            super().perform_create(instance)
            for organization in instance._organizations:  # noqa SLF001
                organization_obj = get_object_or_404(
                    Organization, external_id=organization
                )
                if not AuthorizationController.call(
                    "can_write_questionnaire",
                    self.request.user,
                    org=organization_obj.id,
                ):
                    raise PermissionDenied("Permission Denied for Organization")
                QuestionnaireOrganization.objects.create(
                    questionnaire=instance, organization=organization_obj
                )
            for facility_organization in instance._facility_organizations:  # noqa SLF001
                facility_organization_obj = get_object_or_404(
                    FacilityOrganization,
                    external_id=facility_organization,
                    facility=instance.facility,
                )
                # no need to check for permission here as the facility_organization
                # is already filtered by the facility
                QuestionnaireFacilityOrganization.objects.create(
                    questionnaire=instance,
                    facility_organization=facility_organization_obj,
                )

    def validate_data(self, instance, model_obj=None):
        # If we're editing an existing questionnaire (model_obj is not None)
        # and there are no responses linked to this questionnaire yet
        if (
            model_obj
            and model_obj.facility
            and QuestionnaireResponse.objects.filter(questionnaire=model_obj).exists()
        ):
            # Prevent editing if the questionnaire has already been used (has responses)
            # This ensures data integrity by not allowing changes to questionnaires
            # that are actively being used
            raise ValidationError("Cannot edit an active questionnaire")

    def get_queryset(self):
        queryset = super().get_queryset()
        facility = self.get_facility_object()
        queryset = AuthorizationController.call(
            "get_filtered_questionnaires",
            queryset,
            self.request.user,
            facility=facility,
        )
        return queryset.select_related("created_by", "updated_by")

    @extend_schema(
        request=QuestionnaireSubmitRequest,
        responses=QuestionnaireResponseReadSpec,
    )
    @action(detail=True, methods=["POST"])
    def submit(self, request, *args, **kwargs):
        request_params = QuestionnaireSubmitRequest(**request.data)
        questionnaire = self.get_object()
        patient = get_object_or_404(Patient, external_id=request_params.patient)
        if request_params.encounter:
            encounter = get_object_or_404(
                Encounter, external_id=request_params.encounter, patient=patient
            )
            if not AuthorizationController.call(
                "can_submit_encounter_questionnaire_obj", request.user, encounter
            ):
                raise PermissionDenied(
                    "Permission Denied to submit patient questionnaire"
                )
        elif not AuthorizationController.call(
            "can_submit_questionnaire_patient_obj", request.user, patient
        ):
            raise PermissionDenied("Permission Denied to submit patient questionnaire")
        with transaction.atomic():
            response = handle_response(questionnaire, request_params, request.user)
        return Response(QuestionnaireResponseReadSpec.serialize(response).to_json())

    @action(detail=True, methods=["GET"])
    def get_organizations(self, request, *args, **kwargs):
        """
        Get all External Organizations connected to this Questionnaire
        """
        questionnaire = self.get_object()
        if questionnaire.facility:
            organizations_serialized = [
                FacilityOrganizationReadSpec.serialize(
                    obj.facility_organization
                ).to_json()
                for obj in QuestionnaireFacilityOrganization.objects.filter(
                    questionnaire=questionnaire,
                    facility_organization__facility_id=questionnaire.facility.id,
                ).select_related("facility_organization")
            ]
        else:
            organizations_serialized = [
                OrganizationReadSpec.serialize(obj.organization).to_json()
                for obj in QuestionnaireOrganization.objects.filter(
                    questionnaire=questionnaire
                ).select_related("organization")
            ]
        return Response(
            {
                "count": len(organizations_serialized),
                "results": organizations_serialized,
            }
        )

    class QuestionnaireTagsSetSchema(BaseModel):
        tags: list[str]

    @extend_schema(request=QuestionnaireTagsSetSchema)
    @action(detail=True, methods=["POST"])
    def set_tags(self, request, *args, **kwargs):
        questionnaire = self.get_object()
        request_data = self.QuestionnaireTagsSetSchema(**request.data)
        if not AuthorizationController.call(
            "can_write_questionnaire_obj", request.user, questionnaire
        ):
            raise PermissionDenied("Permission Denied for Questionnaire")
        tags = []
        for tag in request_data.tags:
            tags.append(get_object_or_404(QuestionnaireTag, slug=tag).id)
        questionnaire.tags = tags
        questionnaire.save(update_fields=["tags"])
        return Response({})

    class QuestionnaireOrganizationUpdateSchema(BaseModel):
        organizations: list[UUID4]
        facility_organizations: list[UUID4] = []

    @extend_schema(request=QuestionnaireOrganizationUpdateSchema)
    @action(detail=True, methods=["POST"])
    def set_organizations(self, request, *args, **kwargs):
        """
        Bulk Update all External Organizations connected to this Questionnaire
        """
        questionnaire = self.get_object()
        request_params = self.QuestionnaireOrganizationUpdateSchema(**request.data)
        if not AuthorizationController.call(
            "can_write_questionnaire_obj", request.user, questionnaire
        ):
            raise PermissionDenied("Permission Denied for Questionnaire")
        with transaction.atomic():
            if questionnaire.facility:
                QuestionnaireFacilityOrganization.objects.filter(
                    questionnaire=questionnaire,
                    facility_organization__facility_id=questionnaire.facility.id,
                ).delete()
                for org in request_params.facility_organizations:
                    facility_organization = get_object_or_404(
                        FacilityOrganization,
                        external_id=org,
                        facility=questionnaire.facility,
                    )
                    # no need to check for permission here as the facility_organization
                    # is already filtered by the facility
                    QuestionnaireFacilityOrganization.objects.create(
                        questionnaire=questionnaire,
                        facility_organization=facility_organization,
                    )
                organizations_serialized = [
                    FacilityOrganizationReadSpec.serialize(
                        obj.facility_organization
                    ).to_json()
                    for obj in QuestionnaireFacilityOrganization.objects.filter(
                        questionnaire=questionnaire,
                        facility_organization__facility_id=questionnaire.facility.id,
                    ).select_related("facility_organization")
                ]
            else:
                QuestionnaireOrganization.objects.filter(
                    questionnaire=questionnaire
                ).delete()
                for org in request_params.organizations:
                    organization = get_object_or_404(Organization, external_id=org)
                    if not AuthorizationController.call(
                        "can_write_questionnaire", request.user, org=organization.id
                    ):
                        raise PermissionDenied("Permission Denied for Organization")
                    QuestionnaireOrganization.objects.create(
                        questionnaire=questionnaire, organization=organization
                    )
                organizations_serialized = [
                    OrganizationReadSpec.serialize(obj.organization).to_json()
                    for obj in QuestionnaireOrganization.objects.filter(
                        questionnaire=questionnaire
                    ).select_related("organization")
                ]

        return Response(
            {
                "count": len(organizations_serialized),
                "results": organizations_serialized,
            }
        )
