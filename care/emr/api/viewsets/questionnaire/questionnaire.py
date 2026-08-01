from django.db import transaction
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.api.viewsets.favorites import EMRFavoritesMixin
from care.emr.api.viewsets.questionnaire.resource_authz import (
    authorize_resource_questionnaire_submission,
    get_resource_facility,
)
from care.emr.locks.questionnaire import QuestionnaireLock
from care.emr.models import (
    Encounter,
    Organization,
    Patient,
    Questionnaire,
    QuestionnaireOrganization,
)
from care.emr.models.device import Device
from care.emr.models.location import FacilityLocation
from care.emr.models.organization import FacilityOrganization
from care.emr.models.questionnaire import (
    FormSubmission,
    QuestionnaireFacilityOrganization,
    QuestionnaireResponse,
)
from care.emr.resources.facility_organization.spec import FacilityOrganizationReadSpec
from care.emr.resources.favorites.filters import FavoritesFilter
from care.emr.resources.favorites.spec import FavoriteResourceChoices
from care.emr.resources.form_submission.spec import FormSubmissionStatusChoices
from care.emr.resources.organization.spec import OrganizationReadSpec
from care.emr.resources.questionnaire.spec import (
    QuestionnaireAuthContext,
    QuestionnaireCreateSpec,
    QuestionnaireReadSpec,
    QuestionnaireUpdateSpec,
    SubjectType,
)
from care.emr.resources.questionnaire.utils import (
    handle_resource_response,
    handle_response,
)
from care.emr.resources.questionnaire_response.resource_spce import (
    ResourceQuestionnaireResponseReadSpec,
    ResourceQuestionnaireSubmitRequest,
)
from care.emr.resources.questionnaire_response.spec import (
    QuestionnaireResponseReadSpec,
    QuestionnaireSubmitRequest,
)
from care.facility.models.facility import Facility
from care.security.authorization import AuthorizationController
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.lock import ObjectLocked
from care.utils.shortcuts import get_object_or_404


class ParentRevisionFilter(filters.UUIDFilter):
    def filter(self, qs, value):
        if value is None:
            return qs.filter(latest_revision__isnull=True)
        return qs.filter(latest_revision__external_id=value)


class QuestionnaireFilter(filters.FilterSet):
    title = filters.CharFilter(field_name="title", lookup_expr="icontains")
    subject_type = MultiSelectFilter(field_name="subject_type")
    auth_context = filters.CharFilter(field_name="auth_context", lookup_expr="iexact")
    facility = filters.UUIDFilter(field_name="facility__external_id")
    status = filters.CharFilter(field_name="status", lookup_expr="iexact")
    parent_revision = ParentRevisionFilter()


class QuestionnaireViewSet(EMRModelViewSet, EMRFavoritesMixin):
    database_model = Questionnaire
    pydantic_model = QuestionnaireCreateSpec
    pydantic_read_model = QuestionnaireReadSpec
    pydantic_update_model = QuestionnaireUpdateSpec
    filterset_class = QuestionnaireFilter
    filter_backends = [filters.DjangoFilterBackend, FavoritesFilter]
    FAVORITE_RESOURCE = FavoriteResourceChoices.questionnaire.value

    def retrieve_facility_obj(self, obj):
        return obj.facility

    def get_serializer_create_context(self):
        return {"user": self.request.user}

    def get_serializer_update_context(self):
        return {"user": self.request.user}

    def handle_update(self, instance, request_data):
        lock = QuestionnaireLock(instance)
        try:
            lock.acquire()
        except ObjectLocked as e:
            raise ValidationError(
                "Questionnaire update failed, try again after a while"
            ) from e
        try:
            with transaction.atomic():
                instance.refresh_from_db()
                transaction.on_commit(lock.release)
                return super().handle_update(instance, request_data)
        except Exception:
            lock.release()
            raise

    def authorize_update(self, request_obj, model_instance):
        if model_instance.latest_revision:
            raise PermissionDenied(
                "This Questionnaire is a past revision, please update the latest revision"
            )
        if (
            model_instance.auth_context == QuestionnaireAuthContext.instance
            and not self.request.user.is_superuser
        ):
            raise PermissionDenied("Only Superusers can edit a questionnaire")
        if (
            model_instance.auth_context == QuestionnaireAuthContext.facility
            and not AuthorizationController.call(
                "can_access_facility_questionnaire",
                self.request.user,
                model_instance.facility,
                model_instance,
                read_only=False,
            )
        ):
            raise PermissionDenied("Permission Denied to update facility questionnaire")
        if (
            model_instance.auth_context
            == QuestionnaireAuthContext.facility_organization
            and not AuthorizationController.call(
                "can_access_facility_organization_questionnaire",
                self.request.user,
                model_instance.facility_organization,
                read_only=False,
            )
        ):
            raise PermissionDenied(
                "Permission Denied to update facility organization questionnaire"
            )
        if (
            model_instance.auth_context == QuestionnaireAuthContext.user
            and model_instance.created_by != self.request.user
        ):
            raise PermissionDenied(
                "Only the creator of the questionnaire can update it"
            )
        if (
            model_instance.auth_context == QuestionnaireAuthContext.user
            and not AuthorizationController.call(
                "can_access_user_questionnaire_in_faciltiy",
                self.request.user,
                model_instance.facility,
                read_only=False,
            )
        ):
            raise PermissionDenied("Permission Denied to create user questionnaire")

    def authorize_create(self, instance):
        if (
            instance.auth_context == QuestionnaireAuthContext.instance
            and not self.request.user.is_superuser
        ):
            raise PermissionDenied(
                "Only Superusers can create an instance level questionnaire"
            )
        if instance.auth_context == QuestionnaireAuthContext.facility:
            facility = get_object_or_404(Facility, external_id=instance.facility)
            if not AuthorizationController.call(
                "can_access_facility_questionnaire",
                self.request.user,
                facility,
                None,
                read_only=False,
            ):
                raise PermissionDenied(
                    "Permission Denied to create facility questionnaire"
                )
        elif instance.auth_context == QuestionnaireAuthContext.facility_organization:
            facility_organization = get_object_or_404(
                FacilityOrganization, external_id=instance.facility_organization
            )
            if not AuthorizationController.call(
                "can_access_facility_organization_questionnaire",
                self.request.user,
                facility_organization,
                read_only=False,
            ):
                raise PermissionDenied(
                    "Permission Denied to create facility organization questionnaire"
                )
        elif instance.auth_context == QuestionnaireAuthContext.user:
            facility = get_object_or_404(Facility, external_id=instance.facility)
            if not AuthorizationController.call(
                "can_access_user_questionnaire_in_faciltiy",
                self.request.user,
                facility,
                read_only=False,
            ):
                raise PermissionDenied("Permission Denied to create user questionnaire")

    def authorize_destroy(self, instance):
        self.authorize_update(self.request, instance)

    def get_queryset(self):
        queryset = super().get_queryset()
        return AuthorizationController.call(
            "get_filtered_questionnaires", queryset, self.request.user
        )

    @extend_schema(
        request=ResourceQuestionnaireSubmitRequest,
        responses=ResourceQuestionnaireResponseReadSpec,
    )
    @action(detail=True, methods=["POST"])
    def submit_resource(self, request, *args, **kwargs):
        request_params = ResourceQuestionnaireSubmitRequest(**request.data)
        questionnaire = self.get_object()
        if questionnaire.latest_revision:
            raise ValidationError(
                "This Questionniare is a past revision, please submit to the latest revision"
            )
        resource = None
        if questionnaire.subject_type == SubjectType.location:
            resource = get_object_or_404(
                FacilityLocation, external_id=request_params.resource_id
            )
        elif questionnaire.subject_type == SubjectType.device:
            resource = get_object_or_404(Device, external_id=request_params.resource_id)
        elif questionnaire.subject_type == SubjectType.facility:
            resource = get_object_or_404(
                Facility, external_id=request_params.resource_id
            )
        else:
            err = f"Invalid resource type: {questionnaire.subject_type}"
            raise ValidationError(err)
        authorize_resource_questionnaire_submission(
            questionnaire.subject_type, resource, request.user
        )
        facility = get_resource_facility(questionnaire.subject_type, resource)
        if questionnaire.facility_id and facility.id != questionnaire.facility_id:
            raise PermissionDenied(
                "Resource facility does not match questionnaire facility"
            )
        with transaction.atomic():
            response = handle_resource_response(
                questionnaire, request_params, request.user, facility
            )
            response.revision = questionnaire.internal_revision
            response.save(update_fields=["revision"])
        return Response(
            ResourceQuestionnaireResponseReadSpec.serialize(response).to_json()
        )

    @extend_schema(
        request=QuestionnaireSubmitRequest,
        responses=QuestionnaireResponseReadSpec,
    )
    @action(detail=True, methods=["POST"])
    def submit(self, request, *args, **kwargs):
        request_params = QuestionnaireSubmitRequest(**request.data)
        questionnaire = self.get_object()
        if questionnaire.latest_revision:
            raise ValidationError(
                "This Questionniare is a past revision, please submit to the latest revision"
            )
        patient = get_object_or_404(Patient, external_id=request_params.patient)
        form_submission_params = {"patient": patient}
        if questionnaire.subject_type == SubjectType.encounter:
            if not request_params.encounter:
                raise ValidationError("Encounter is required for this questionnaire")
            encounter = get_object_or_404(
                Encounter, external_id=request_params.encounter, patient=patient
            )
            if (
                questionnaire.facility_id
                and encounter.facility_id != questionnaire.facility_id
            ):
                raise PermissionDenied(
                    "Encounter facility does not match questionnaire facility"
                )
            if not AuthorizationController.call(
                "can_submit_encounter_questionnaire_obj", request.user, encounter
            ):
                raise PermissionDenied(
                    "Permission Denied to submit encounter questionnaire"
                )
            form_submission_params["encounter"] = encounter
        else:
            if request_params.encounter:
                raise ValidationError(
                    "Encounter cannot be provided for a patient questionnaire"
                )
            if not AuthorizationController.call(
                "can_submit_questionnaire_patient_obj", request.user, patient
            ):
                raise PermissionDenied(
                    "Permission Denied to submit patient questionnaire"
                )
            form_submission_params["encounter__isnull"] = True
        with transaction.atomic():
            response = handle_response(questionnaire, request_params, request.user)
            response.revision = questionnaire.internal_revision
            response.save(update_fields=["revision"])
            if request_params.form_submission:
                form_submission = get_object_or_404(
                    FormSubmission,
                    status=FormSubmissionStatusChoices.draft.value,
                    external_id=request_params.form_submission,
                    questionnaire=questionnaire,
                    **form_submission_params,
                )
                if QuestionnaireResponse.objects.filter(
                    form_submission=form_submission,
                    questionnaire=questionnaire,
                ).exists():
                    raise ValidationError("Form submission already has a response")
                response.form_submission = form_submission
                response.updated_by = request.user
                response.save(
                    update_fields=["form_submission", "updated_by", "modified_date"]
                )
        return Response(QuestionnaireResponseReadSpec.serialize(response).to_json())

    @action(detail=True, methods=["GET"])
    def get_facility_organizations(self, request, *args, **kwargs):
        questionnaire = self.get_object()
        if not questionnaire.auth_context == QuestionnaireAuthContext.facility:
            raise PermissionDenied(
                "Facility organizations can only be set for facility level questionnaires"
            )
        self.authorize_update(None, questionnaire)
        questionnaire_organizations = QuestionnaireFacilityOrganization.objects.filter(
            questionnaire=questionnaire
        ).select_related("organization")
        organizations_serialized = [
            FacilityOrganizationReadSpec.serialize(obj.organization).to_json()
            for obj in questionnaire_organizations
        ]
        return Response(
            {
                "count": len(organizations_serialized),
                "results": organizations_serialized,
            }
        )

    class QuestionnaireFacilityOrganizationUpdateSchema(BaseModel):
        facility_organizations: list[UUID4]

    @extend_schema(request=QuestionnaireFacilityOrganizationUpdateSchema)
    @action(detail=True, methods=["POST"])
    def set_facility_organizations(self, request, *args, **kwargs):
        questionnaire = self.get_object()
        if not questionnaire.auth_context == QuestionnaireAuthContext.facility:
            raise PermissionDenied(
                "Facility organizations can only be set for facility level questionnaires"
            )
        self.authorize_update(None, questionnaire)
        request_params = self.QuestionnaireFacilityOrganizationUpdateSchema(
            **request.data
        )
        with transaction.atomic():
            QuestionnaireFacilityOrganization.objects.filter(
                questionnaire=questionnaire
            ).delete()
            for org in request_params.facility_organizations:
                organization = get_object_or_404(
                    FacilityOrganization.objects.only("id"),
                    external_id=org,
                    facility=questionnaire.facility,
                )
                QuestionnaireFacilityOrganization.objects.create(
                    questionnaire=questionnaire, organization=organization
                )
            questionnaire.sync_facility_org_cache()
        return Response({})

    @action(detail=True, methods=["GET"])
    def get_organizations(self, request, *args, **kwargs):
        """
        Get all External Organizations connected to this Questionnaire
        """
        questionnaire = self.get_object()
        if not questionnaire.auth_context == QuestionnaireAuthContext.instance:
            raise PermissionDenied(
                "Organizations can only be set for instance level questionnaires"
            )
        self.authorize_update(request, questionnaire)  # Restrict access to only admins
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

    class QuestionnaireOrganizationUpdateSchema(BaseModel):
        organizations: list[UUID4]

    @extend_schema(request=QuestionnaireOrganizationUpdateSchema)
    @action(detail=True, methods=["POST"])
    def set_organizations(self, request, *args, **kwargs):
        """
        Bulk Update all External Organizations connected to this Questionnaire
        """
        questionnaire = self.get_object()
        if not questionnaire.auth_context == QuestionnaireAuthContext.instance:
            raise PermissionDenied(
                "Organizations can only be set for instance level questionnaires"
            )
        self.authorize_update(request, questionnaire)
        request_params = self.QuestionnaireOrganizationUpdateSchema(**request.data)
        with transaction.atomic():
            QuestionnaireOrganization.objects.filter(
                questionnaire=questionnaire
            ).delete()
            for org in request_params.organizations:
                organization = get_object_or_404(
                    Organization.objects.only("id"), external_id=org
                )
                QuestionnaireOrganization.objects.create(
                    questionnaire=questionnaire, organization=organization
                )
            questionnaire.sync_org_cache()
        return Response({})
