from copy import deepcopy
from uuid import UUID

from django.db import IntegrityError, transaction
from django.http import Http404
from django_filters import rest_framework as filters
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from pydantic import BaseModel, Field
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRDestroyMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.emr.api.viewsets.questionnaire.questionnaire import QuestionnaireViewSet
from care.emr.models import Encounter
from care.emr.models.consent import Consent
from care.emr.models.file_upload import FileUpload
from care.emr.models.notes import NoteMessage, NoteThread
from care.emr.models.organization import FacilityOrganization, Organization
from care.emr.models.patient import Patient
from care.emr.models.questionnaire import Questionnaire
from care.emr.models.referral import (
    Referral,
    ReferralAvailability,
    ReferralAvailabilityQuestionnaire,
    ReferralQuestionnaireResponse,
    ReferralResource,
)
from care.emr.resources.notes.constants import NoteThreadType
from care.emr.resources.notes.notes_spec import (
    NoteMessageCreateSpec,
    NoteMessageReadSpec,
    NoteMessageUpdateSpec,
)
from care.emr.resources.notes.thread_spec import NoteThreadReadSpec
from care.emr.resources.questionnaire.spec import QuestionnaireReadSpec
from care.emr.resources.questionnaire.utils import validate_questionnaire_response
from care.emr.resources.questionnaire_response.spec import (
    QuestionnaireResponseStatusChoices,
    QuestionnaireResponseSubmission,
)
from care.emr.resources.referral.availability import (
    ReferralAvailabilityConfigQuerySpec,
    ReferralAvailabilityCreateSpec,
    ReferralAvailabilityQuerySpec,
    ReferralAvailabilityReadSpec,
    ReferralAvailabilityRetrieveSpec,
    ReferralAvailabilityUpdateSpec,
)
from care.emr.resources.referral.common import (
    ReferralEntityType,
    ReferralQuestionnaireType,
)
from care.emr.resources.referral.spec import (
    ReferralAssigneesWriteSpec,
    ReferralCreateSpec,
    ReferralListQuerySpec,
    ReferralQuestionnaireResponseCreateSpec,
    ReferralQuestionnaireResponseReadSpec,
    ReferralReadSpec,
    ReferralResourceCreateSpec,
    ReferralResourceReadSpec,
    ReferralResourceType,
    ReferralRetrieveSpec,
    ReferralUpdateSpec,
)
from care.emr.utils.resource_reference import get_resource_handler
from care.facility.models.facility import Facility
from care.security.authorization import AuthorizationController
from care.users.models import User
from care.utils.shortcuts import get_object_or_404

PENDING_REFERRAL_STATUSES = ["pending", "in_progress"]


class ReferralQuestionnaireReadSpec(QuestionnaireReadSpec):
    questionnaire_type: ReferralQuestionnaireType


class ReferralQuestionnaireListSpec(BaseModel):
    count: int
    results: list[ReferralQuestionnaireReadSpec]


class ReferralListSpec(BaseModel):
    count: int
    results: list[ReferralReadSpec]


class ReferralQuestionnaireQuerySpec(BaseModel):
    questionnaire_type: ReferralQuestionnaireType | None = None


def authorize_referral(user, referral, *, write=False):
    permission = "can_write_referral" if write else "can_read_referral"
    if not AuthorizationController.call(permission, user, referral):
        raise PermissionDenied("Permission denied to referral")


def prepare_referral_questionnaire_response(
    instance, *, expected_questionnaire_type=None
):
    referral = instance.referral
    questionnaire = get_object_or_404(
        Questionnaire.objects.select_for_update(), id=instance.questionnaire_id
    )
    mapping = referral.availability.questionnaire_mappings.filter(
        questionnaire=questionnaire
    ).first()
    if mapping is None:
        raise ValidationError("Questionnaire is not mapped to this availability")
    if (
        expected_questionnaire_type is not None
        and mapping.questionnaire_type != expected_questionnaire_type
    ):
        raise ValidationError("A request questionnaire is required to start a referral")
    if questionnaire.latest_revision_id:
        raise ValidationError("A current questionnaire is required")
    if questionnaire.subject_type not in ("patient", "encounter"):
        raise ValidationError("Referral forms must target a patient or encounter")
    if not referral.encounter_id and questionnaire.subject_type != "patient":
        raise ValidationError(
            "A patient referral without an encounter requires a patient questionnaire"
        )
    submission = QuestionnaireResponseSubmission.model_validate(
        instance.questionnaire_response
    )
    validated = validate_questionnaire_response(questionnaire, submission.results)
    instance.questionnaire = questionnaire
    instance.questionnaire_type = mapping.questionnaire_type
    instance.questionnaire_response = {
        **submission.model_dump(mode="json"),
        "cleaned_response": validated.cleaned_response,
    }
    instance.questionnaire_revision = questionnaire.internal_revision
    instance.questionnaire_snapshot = QuestionnaireReadSpec.serialize(
        questionnaire
    ).to_json()


def set_referral_questionnaires(instance):
    questionnaire_types = instance._questionnaire_types  # noqa: SLF001
    instance.questionnaire_mappings.exclude(
        questionnaire_id__in=questionnaire_types
    ).delete()
    for questionnaire in instance._questionnaires:  # noqa: SLF001
        ReferralAvailabilityQuestionnaire.objects.update_or_create(
            availability=instance,
            questionnaire=questionnaire,
            defaults={"questionnaire_type": questionnaire_types[questionnaire.id]},
        )


def render_referral_questionnaires(
    availability, query_params, *, subject_types=("patient", "encounter")
):
    query = ReferralQuestionnaireQuerySpec.model_validate(query_params.dict())
    mappings = availability.questionnaire_mappings.filter(
        questionnaire__deleted=False,
        questionnaire__status="active",
        questionnaire__latest_revision__isnull=True,
        questionnaire__subject_type__in=subject_types,
    ).select_related("questionnaire")
    if query.questionnaire_type is not None:
        mappings = mappings.filter(questionnaire_type=query.questionnaire_type.value)
    results = [
        {
            **QuestionnaireReadSpec.serialize(mapping.questionnaire).to_json(),
            "questionnaire_type": mapping.questionnaire_type,
        }
        for mapping in mappings
    ]
    return {"count": len(results), "results": results}


class ReferralAvailabilityFilters(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="icontains")
    entity_type = filters.CharFilter(lookup_expr="exact")
    status = filters.CharFilter(lookup_expr="exact")
    referral_type = filters.CharFilter(lookup_expr="exact")
    is_public = filters.BooleanFilter()
    facility = filters.UUIDFilter(field_name="facility__external_id")
    internal_organization = filters.UUIDFilter(
        field_name="internal_organization__external_id"
    )
    external_organization = filters.UUIDFilter(
        field_name="external_organization__external_id"
    )


class ReferralAvailabilityBaseViewSet(EMRBaseViewSet):
    database_model = ReferralAvailability
    pydantic_read_model = ReferralAvailabilityReadSpec
    pydantic_retrieve_model = ReferralAvailabilityRetrieveSpec
    filterset_class = ReferralAvailabilityFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["name", "created_date", "modified_date"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "facility", "external_organization", "internal_organization"
            )
        )


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "entity_type",
                enum=[entity.value for entity in ReferralEntityType],
                required=True,
                description="Browse active referral destinations of this entity type.",
            )
        ]
    ),
    create=extend_schema(responses={200: ReferralAvailabilityRetrieveSpec}),
    update=extend_schema(responses={200: ReferralAvailabilityRetrieveSpec}),
    partial_update=extend_schema(responses={200: ReferralAvailabilityRetrieveSpec}),
)
class ReferralAvailabilityViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRDestroyMixin,
    ReferralAvailabilityBaseViewSet,
):
    pydantic_model = ReferralAvailabilityCreateSpec
    pydantic_update_model = ReferralAvailabilityUpdateSpec

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action != "list":
            return queryset
        query = ReferralAvailabilityQuerySpec.model_validate(
            self.request.query_params.dict()
        )
        return AuthorizationController.call(
            "get_accessible_referral_availabilities",
            queryset,
            self.request.user,
            query.entity_type.value,
        )

    def authorize_manage(self, instance):
        if not AuthorizationController.call(
            "can_manage_referral_availability", self.request.user, instance
        ):
            raise PermissionDenied("Permission denied to manage referral availability")

    def authorize_create(self, instance):
        candidate = instance.de_serialize()
        candidate.created_by = self.request.user
        self.authorize_manage(candidate)
        self.authorize_questionnaires(candidate)

    def authorize_retrieve(self, instance):
        if not AuthorizationController.call(
            "can_view_referral_availability", self.request.user, instance
        ):
            raise Http404("No ReferralAvailability matches the given query.")

    def authorize_update(self, request_obj, model_instance):
        self.authorize_manage(model_instance)
        self.authorize_questionnaires(request_obj.de_serialize(obj=model_instance))

    def authorize_destroy(self, instance):
        self.authorize_manage(instance)

    def authorize_questionnaires(self, instance):
        # Publishing a form delegates its rendering to availability users.
        # The publisher must first be allowed to read the original form.
        view = QuestionnaireViewSet()
        view.request = self.request
        for questionnaire in getattr(instance, "_questionnaires", []):
            if questionnaire.status != "active" or questionnaire.latest_revision_id:
                raise ValidationError(
                    "Only active, current questionnaires can be mapped"
                )
            if questionnaire.subject_type not in ("patient", "encounter"):
                raise ValidationError(
                    "Referral forms must target a patient or encounter"
                )
            view.authorize_retrieve(questionnaire)

    def perform_create(self, instance):
        with transaction.atomic():
            super().perform_create(instance)
            set_referral_questionnaires(instance)

    def perform_update(self, instance):
        with transaction.atomic():
            super().perform_update(instance)
            if hasattr(instance, "_questionnaires"):
                set_referral_questionnaires(instance)

    def handle_update(self, instance, request_data):
        with transaction.atomic():
            instance = get_object_or_404(ReferralAvailability, id=instance.id)
            return super().handle_update(instance, request_data)

    @extend_schema(responses=ReferralQuestionnaireListSpec)
    @action(detail=True, methods=["GET"])
    def questionnaires(self, request, *args, **kwargs):
        availability = self.get_object()
        self.authorize_retrieve(availability)
        return Response(
            render_referral_questionnaires(availability, request.query_params)
        )


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "entity_type",
                enum=[
                    entity.value
                    for entity in ReferralEntityType
                    if entity != ReferralEntityType.external
                ],
                required=True,
                description="The destination entity whose configuration is managed.",
            ),
            OpenApiParameter("entity_id", type=OpenApiTypes.UUID, required=True),
        ]
    )
)
class ReferralAvailabilityConfigViewSet(EMRListMixin, ReferralAvailabilityBaseViewSet):
    def get_queryset(self):
        query = ReferralAvailabilityConfigQuerySpec.model_validate(
            self.request.query_params.dict()
        )
        entity_models = {
            ReferralEntityType.facility: Facility,
            ReferralEntityType.internal_organization: FacilityOrganization,
            ReferralEntityType.external_organization: Organization,
        }
        entity = get_object_or_404(
            entity_models[query.entity_type], external_id=query.entity_id
        )
        scope = ReferralAvailability(
            entity_type=query.entity_type.value, **{query.entity_type.value: entity}
        )
        if not AuthorizationController.call(
            "can_manage_referral_availability", self.request.user, scope
        ):
            raise PermissionDenied("Permission denied to manage referral availability")
        return (
            super()
            .get_queryset()
            .filter(
                entity_type=query.entity_type.value,
                **{f"{query.entity_type.value}_id": entity.id},
            )
        )


class ReferralFilters(filters.FilterSet):
    availability = filters.UUIDFilter(field_name="availability__external_id")
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    patient = filters.UUIDFilter(field_name="patient__external_id")
    facility = filters.UUIDFilter(field_name="availability__facility__external_id")
    internal_organization = filters.UUIDFilter(
        field_name="availability__internal_organization__external_id"
    )
    external_organization = filters.UUIDFilter(
        field_name="availability__external_organization__external_id"
    )
    status = filters.CharFilter(lookup_expr="exact")
    referral_type = filters.CharFilter(field_name="availability__referral_type")
    assigned_to = filters.UUIDFilter(method="filter_assigned_to")
    assigned_to_me = filters.BooleanFilter(method="filter_assigned_to_me")
    pending = filters.BooleanFilter(method="filter_pending")

    def filter_assigned_to(self, queryset, name, value):
        user = User.objects.filter(external_id=value, is_active=True).first()
        return (
            queryset.filter(assignee_users__overlap=[user.id])
            if user
            else queryset.none()
        )

    def filter_assigned_to_me(self, queryset, name, value):
        if value:
            return queryset.filter(assignee_users__overlap=[self.request.user.id])
        return queryset

    def filter_pending(self, queryset, name, value):
        if value:
            return queryset.filter(status__in=PENDING_REFERRAL_STATUSES)
        return queryset.exclude(status__in=PENDING_REFERRAL_STATUSES)


class ReferralThreadWriteSpec(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)


class ReferralBaseViewSet(EMRBaseViewSet):
    database_model = Referral
    pydantic_read_model = ReferralReadSpec
    filterset_class = ReferralFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date", "status"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("availability", "patient", "encounter", "thread")
        )


class AssignedReferralViewSet(EMRListMixin, ReferralBaseViewSet):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(assignee_users__overlap=[self.request.user.id])
        )


@extend_schema_view(
    list=extend_schema(
        description=(
            "Supply entity_type and entity_id, an encounter, or a patient. "
            "Entity scope takes precedence, followed by encounter and patient. "
            "Additional patient and encounter filters only narrow the chosen scope."
        ),
        parameters=[
            OpenApiParameter(
                "entity_type",
                enum=[
                    entity.value
                    for entity in ReferralEntityType
                    if entity != ReferralEntityType.external
                ],
                description="Destination entity type; requires entity_id.",
            ),
            OpenApiParameter(
                "entity_id",
                type=OpenApiTypes.UUID,
                description="Destination entity UUID; requires entity_type.",
            ),
            OpenApiParameter(
                "encounter",
                type=OpenApiTypes.UUID,
                description="Authorize this encounter when no entity scope is supplied.",
            ),
            OpenApiParameter(
                "patient",
                type=OpenApiTypes.UUID,
                description=(
                    "Authorize this patient when no entity or encounter scope is supplied."
                ),
            ),
        ],
    )
)
class ReferralViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    ReferralBaseViewSet,
):
    pydantic_model = ReferralCreateSpec
    pydantic_update_model = ReferralUpdateSpec
    pydantic_retrieve_model = ReferralRetrieveSpec

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action != "list":
            return queryset
        query = ReferralListQuerySpec.model_validate(self.request.query_params.dict())
        if query.entity_type:
            entity_models = {
                ReferralEntityType.facility: Facility,
                ReferralEntityType.internal_organization: FacilityOrganization,
                ReferralEntityType.external_organization: Organization,
            }
            entity = get_object_or_404(
                entity_models[query.entity_type], external_id=query.entity_id
            )
            scope = ReferralAvailability(
                entity_type=query.entity_type.value,
                **{query.entity_type.value: entity},
            )
            permission = "can_list_entity_referrals"
            queryset = queryset.filter(
                availability__entity_type=query.entity_type.value,
                **{f"availability__{query.entity_type.value}_id": entity.id},
            )
        elif query.encounter:
            scope = get_object_or_404(
                Encounter.objects.select_related("current_location"),
                external_id=query.encounter,
            )
            permission = "can_list_encounter_referrals"
            queryset = queryset.filter(encounter=scope)
        else:
            scope = get_object_or_404(Patient, external_id=query.patient)
            permission = "can_list_patient_referrals"
            queryset = queryset.filter(patient=scope)
        if not AuthorizationController.call(permission, self.request.user, scope):
            raise PermissionDenied("Permission denied to list referrals in this scope")
        return queryset

    def authorize_create(self, instance):
        candidate = instance.de_serialize()
        if not AuthorizationController.call(
            "can_create_referral",
            self.request.user,
            candidate.encounter,
            candidate.availability,
            patient=candidate.patient,
        ):
            raise PermissionDenied("Permission denied to submit referral")

    def authorize_update(self, request_obj, model_instance):
        authorize_referral(self.request.user, model_instance, write=True)

    def authorize_retrieve(self, instance):
        authorize_referral(self.request.user, instance)

    def handle_update(self, instance, request_data):
        with transaction.atomic():
            instance = get_object_or_404(
                Referral.objects.select_for_update(), id=instance.id
            )
            return super().handle_update(instance, request_data)

    def perform_create(self, instance):
        with transaction.atomic():
            availability = get_object_or_404(
                ReferralAvailability,
                id=instance.availability_id,
            )
            if not AuthorizationController.call(
                "can_create_referral",
                self.request.user,
                instance.encounter,
                availability,
                patient=instance.patient,
            ):
                raise PermissionDenied("Permission denied to submit referral")
            response = instance._initial_questionnaire_response  # noqa: SLF001
            response.referral = instance
            prepare_referral_questionnaire_response(
                response,
                expected_questionnaire_type=ReferralQuestionnaireType.request.value,
            )
            instance.assignees = deepcopy(availability.care_team)
            super().perform_create(instance)
            response.referral = instance
            response.created_by = self.request.user
            response.updated_by = self.request.user
            response.save()

    @extend_schema(request=ReferralAssigneesWriteSpec, responses=ReferralRetrieveSpec)
    @action(detail=True, methods=["POST"])
    def set_assignees(self, request, *args, **kwargs):
        referral = self.get_object()
        authorize_referral(request.user, referral, write=True)
        data = ReferralAssigneesWriteSpec.model_validate(request.data)
        return Response(
            self.handle_update(
                referral, {"assignees": data.model_dump(mode="json")["members"]}
            )
        )

    @extend_schema(responses=ReferralListSpec)
    @action(detail=True, methods=["GET"], pagination_class=None)
    def referenced_by(self, request, *args, **kwargs):
        referral = self.get_object()
        authorize_referral(request.user, referral)
        references = ReferralResource.objects.filter(
            resource_type=ReferralResourceType.referral.value,
            resource_id=referral.external_id,
        )
        queryset = self.filter_queryset(
            self.get_queryset()
            .filter(
                id__in=references.values("referral_id"),
                patient_id=referral.patient_id,
            )
            .exclude(id=referral.id)
        )
        results = [self.serialize_list(instance) for instance in queryset]
        return Response({"count": len(results), "results": results})

    @extend_schema(responses=ReferralQuestionnaireListSpec)
    @action(detail=True, methods=["GET"])
    def questionnaires(self, request, *args, **kwargs):
        referral = self.get_object()
        authorize_referral(request.user, referral)
        return Response(
            render_referral_questionnaires(
                referral.availability,
                request.query_params,
                subject_types=("patient", "encounter")
                if referral.encounter_id
                else ("patient",),
            )
        )

    @extend_schema(request=ReferralThreadWriteSpec, responses=NoteThreadReadSpec)
    @action(detail=True, methods=["POST", "PUT"])
    def thread(self, request, *args, **kwargs):
        referral = self.get_object()
        authorize_referral(request.user, referral, write=True)
        data = ReferralThreadWriteSpec.model_validate(request.data)
        with transaction.atomic():
            referral = Referral.objects.select_for_update().get(id=referral.id)
            if request.method == "POST":
                if referral.thread_id:
                    raise ValidationError("Referral already has a thread")
                referral.thread = NoteThread.objects.create(
                    thread_type=NoteThreadType.referral.value,
                    patient=referral.patient,
                    encounter=referral.encounter,
                    title=data.title or referral.title,
                    created_by=request.user,
                    updated_by=request.user,
                )
                referral.updated_by = request.user
                referral.save(update_fields=["thread", "updated_by", "modified_date"])
            else:
                if not referral.thread_id:
                    raise ValidationError("Referral has no thread")
                if data.title is None:
                    raise ValidationError("Title is required")
                referral.thread.title = data.title
                referral.thread.updated_by = request.user
                referral.thread.save(
                    update_fields=["title", "updated_by", "modified_date"]
                )
        return Response(NoteThreadReadSpec.serialize(referral.thread).to_json())


class ReferralChildMixin:
    def get_referral(self):
        return get_object_or_404(
            Referral.objects.all(),
            external_id=self.kwargs["referral_external_id"],
        )

    def authorize_create(self, instance):
        authorize_referral(self.request.user, self.get_referral(), write=True)

    def authorize_destroy(self, instance):
        authorize_referral(self.request.user, self.get_referral(), write=True)


class ReferralQuestionnaireResponseFilters(filters.FilterSet):
    questionnaire = filters.UUIDFilter(field_name="questionnaire__external_id")
    status = filters.CharFilter()
    questionnaire_type = filters.CharFilter()


class ReferralQuestionnaireResponseViewSet(
    ReferralChildMixin,
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRDestroyMixin,
    EMRListMixin,
    EMRBaseViewSet,
):
    database_model = ReferralQuestionnaireResponse
    pydantic_model = ReferralQuestionnaireResponseCreateSpec
    pydantic_read_model = ReferralQuestionnaireResponseReadSpec
    filterset_class = ReferralQuestionnaireResponseFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date", "status"]

    def get_referral(self):
        return get_object_or_404(
            Referral, external_id=self.kwargs["referral_external_id"]
        )

    def get_queryset(self):
        referral = self.get_referral()
        queryset = super().get_queryset().filter(referral=referral)
        if self.action in ("list", "retrieve"):
            authorize_referral(self.request.user, referral)
            queryset = queryset.select_related("referral", "questionnaire")
        return queryset

    def perform_create(self, instance):
        with transaction.atomic():
            referral = get_object_or_404(
                Referral.objects.select_for_update(), id=self.get_referral().id
            )
            authorize_referral(self.request.user, referral, write=True)
            instance.referral = referral
            prepare_referral_questionnaire_response(instance)
            super().perform_create(instance)

    def perform_destroy(self, instance):
        with transaction.atomic():
            instance = get_object_or_404(
                ReferralQuestionnaireResponse.objects.select_for_update(),
                id=instance.id,
            )
            instance.status = QuestionnaireResponseStatusChoices.entered_in_error.value
            instance.updated_by = self.request.user
            instance.save(update_fields=["status", "updated_by", "modified_date"])


class ReferralResolvedResourceSpec(BaseModel):
    resource_type: ReferralResourceType
    resource: dict


class ReferralResourceFilters(filters.FilterSet):
    attachment_type = filters.CharFilter()
    resource_type = filters.CharFilter()


class ReferralResourceViewSet(
    ReferralChildMixin,
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRListMixin,
    EMRDestroyMixin,
    EMRBaseViewSet,
):
    database_model = ReferralResource
    pydantic_model = ReferralResourceCreateSpec
    pydantic_read_model = ReferralResourceReadSpec
    filterset_class = ReferralResourceFilters
    filter_backends = [filters.DjangoFilterBackend]

    def get_referral(self):
        return get_object_or_404(
            Referral, external_id=self.kwargs["referral_external_id"]
        )

    def get_queryset(self):
        referral = self.get_referral()
        if self.action in ("list", "retrieve"):
            authorize_referral(self.request.user, referral)
        return super().get_queryset().filter(referral=referral)

    def validate_data(self, instance, model_obj=None):
        referral = self.get_referral()
        authorize_referral(self.request.user, referral, write=True)
        resource_type = instance.resource_type.value
        resource = self.get_resource(referral, resource_type, instance.resource_id)
        if (
            isinstance(resource, FileUpload)
            and resource.file_type == "referral"
            and UUID(resource.associating_id) == referral.external_id
        ):
            return
        get_resource_handler(resource_type).authorize_read(self.request.user, resource)

    def get_resource(self, referral, resource_type, resource_id):
        resource = get_resource_handler(resource_type).get_object(resource_id)
        if isinstance(resource, FileUpload):
            self.validate_file(referral, resource)
        elif resource.patient_id != referral.patient_id:
            raise ValidationError("Resource does not belong to the referral patient")
        elif isinstance(resource, Referral) and resource.id == referral.id:
            raise ValidationError("A referral cannot be attached to itself")
        return resource

    @extend_schema(responses=ReferralResolvedResourceSpec)
    @action(detail=True, methods=["GET"])
    def resolve(self, request, *args, **kwargs):
        referral = self.get_referral()
        authorize_referral(self.request.user, referral)
        attachment = self.get_object()
        resource = self.get_resource(
            self.get_referral(), attachment.resource_type, attachment.resource_id
        )
        return Response(
            {
                "resource_type": attachment.resource_type,
                "resource": get_resource_handler(attachment.resource_type).render(
                    resource
                ),
            }
        )

    def validate_file(self, referral, resource):
        try:
            associating_id = UUID(resource.associating_id)
        except ValueError as error:
            raise ValidationError(
                "File is not an available file for this patient"
            ) from error
        if resource.file_type == "patient":
            same_patient = associating_id == referral.patient.external_id
        elif resource.file_type == "encounter":
            same_patient = Encounter.objects.filter(
                external_id=associating_id, patient_id=referral.patient_id
            ).exists()
        elif resource.file_type in ("diagnostic_report", "service_request"):
            model = get_resource_handler(resource.file_type).model
            same_patient = model.objects.filter(
                external_id=associating_id, patient_id=referral.patient_id
            ).exists()
        elif resource.file_type == "consent":
            same_patient = Consent.objects.filter(
                external_id=associating_id, encounter__patient_id=referral.patient_id
            ).exists()
        elif resource.file_type == "referral":
            same_patient = Referral.objects.filter(
                external_id=associating_id, patient_id=referral.patient_id
            ).exists()
        else:
            same_patient = False
        if not same_patient or not resource.upload_completed or resource.is_archived:
            raise ValidationError("File is not an available file for this patient")

    def perform_create(self, instance):
        instance.referral = self.get_referral()
        try:
            with transaction.atomic():
                super().perform_create(instance)
        except IntegrityError as error:
            raise ValidationError(
                "Resource is already attached to this referral"
            ) from error


class ReferralNoteMessageViewSet(
    ReferralChildMixin,
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
):
    database_model = NoteMessage
    pydantic_model = NoteMessageCreateSpec
    pydantic_update_model = NoteMessageUpdateSpec
    pydantic_read_model = NoteMessageReadSpec

    def get_queryset(self):
        referral = self.get_referral()
        if self.action in ("list", "retrieve"):
            authorize_referral(self.request.user, referral)
        if not referral.thread_id:
            return super().get_queryset().none()
        return super().get_queryset().filter(thread_id=referral.thread_id)

    def perform_create(self, instance):
        referral = self.get_referral()
        if not referral.thread_id:
            raise ValidationError("Referral has no thread")
        instance.thread = referral.thread
        super().perform_create(instance)

    def authorize_update(self, request_obj, model_instance):
        authorize_referral(self.request.user, self.get_referral(), write=True)
        if model_instance.created_by_id != self.request.user.id:
            raise PermissionDenied("Cannot Update Message Created by Other User")
