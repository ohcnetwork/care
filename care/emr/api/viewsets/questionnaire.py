from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
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
    QuestionnaireResponse,
    QuestionnaireTag,
)
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


class QuestionnaireViewSet(EMRModelViewSet):
    database_model = Questionnaire
    pydantic_model = QuestionnaireSpec
    pydantic_read_model = QuestionnaireReadSpec
    pydantic_update_model = QuestionnaireUpdateSpec
    lookup_field = "slug"
    filterset_class = QuestionnaireFilter
    filter_backends = [filters.DjangoFilterBackend]

    def permissions_controller(self, request):
        if self.action in ["list", "retrieve", "get_organizations"]:
            return AuthorizationController.call("can_read_questionnaire", request.user)
        if self.action in ["create", "set_organizations", "set_tags"]:
            return AuthorizationController.call("can_write_questionnaire", request.user)

        return request.user.is_authenticated

    def authorize_update(self, request_obj, model_instance):
        if not self.request.user.is_superuser:
            raise PermissionDenied("Only Superusers can edit a questionnaire")

    def authorize_destroy(self, instance):
        if not self.request.user.is_superuser:
            raise PermissionDenied("Only Superusers can delete a questionnaire")

    def perform_create(self, instance):
        with transaction.atomic():
            super().perform_create(instance)
            for organization in instance._organizations:  # noqa SLF001
                organization_obj = get_object_or_404(
                    Organization, external_id=organization
                )
                QuestionnaireOrganization.objects.create(
                    questionnaire=instance, organization=organization_obj
                )

    def validate_data(self, instance, model_obj=None):
        # If we're editing an existing questionnaire (model_obj is not None)
        # and there are no responses linked to this questionnaire yet
        if (
            model_obj
            and QuestionnaireResponse.objects.filter(questionnaire=model_obj).exists()
        ):
            # Prevent editing if the questionnaire has already been used (has responses)
            # This ensures data integrity by not allowing changes to questionnaires
            # that are actively being used
            raise ValidationError("Cannot edit an active questionnaire")

    def authorize_create(self, instance):
        for org in instance.organizations:
            # Validate if the user has write permission in the organization
            organization = get_object_or_404(Organization, external_id=org)
            if not AuthorizationController.call(
                "can_write_questionnaire", self.request.user, organization.id
            ):
                raise PermissionDenied("Permission Denied for Organization")

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = AuthorizationController.call(
            "get_filtered_questionnaires", queryset, self.request.user
        )
        return queryset.select_related("created_by", "updated_by")

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
        questionnaire_organizations = QuestionnaireOrganization.objects.filter(
            questionnaire=questionnaire
        ).select_related("organization")
        organizations_serialized = [
            OrganizationReadSpec.serialize(obj.organization).to_json()
            for obj in questionnaire_organizations
        ]
        return Response(
            {
                "count": len(organizations_serialized),
                "results": organizations_serialized,
            }
        )

    class QuestionnaireTagsSetSchema(BaseModel):
        tags: list[str]

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
            QuestionnaireOrganization.objects.filter(
                questionnaire=questionnaire
            ).delete()
            for org in request_params.organizations:
                # Validate if the user has write permission in the organization
                organization = get_object_or_404(Organization, external_id=org)
                if not AuthorizationController.call(
                    "can_write_questionnaire", request.user, organization.id
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
