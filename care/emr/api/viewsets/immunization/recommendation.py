from datetime import timedelta

from django.db import transaction
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic.experimental.missing_sentinel import MISSING
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
    EMRUpdateMixin,
)
from care.emr.models.encounter import Encounter
from care.emr.models.immunisation import ImmunizationPolicy, ImmunizationRecommendation
from care.emr.models.patient import Patient
from care.emr.resources.immunisation.policy import (
    ImmunizationPolicyApplyResponseSpec,
    ImmunizationPolicyApplySpec,
    ImmunizationPolicyTemplateSpec,
)
from care.emr.resources.immunisation.recommendation import (
    ImmunizationRecommendationCreateSpec,
    ImmunizationRecommendationForecastStatus,
    ImmunizationRecommendationListSpec,
    ImmunizationRecommendationRetrieveSpec,
    ImmunizationRecommendationUpdateSpec,
)
from care.security.authorization.base import AuthorizationController
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.shortcuts import get_object_or_404


class ImmunizationRecommendationFilters(filters.FilterSet):
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    parent = filters.UUIDFilter(field_name="parent__external_id")
    root = filters.BooleanFilter(field_name="parent", lookup_expr="isnull")
    is_group = filters.BooleanFilter()
    forecast_status = MultiSelectFilter(field_name="forecast_status")
    due_date_after = filters.DateFilter(field_name="due_date", lookup_expr="gte")
    due_date_before = filters.DateFilter(field_name="due_date", lookup_expr="lte")


class ImmunizationRecommendationViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
):
    database_model = ImmunizationRecommendation
    pydantic_model = ImmunizationRecommendationCreateSpec
    pydantic_update_model = ImmunizationRecommendationUpdateSpec
    pydantic_read_model = ImmunizationRecommendationListSpec
    pydantic_retrieve_model = ImmunizationRecommendationRetrieveSpec
    filterset_class = ImmunizationRecommendationFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date", "due_date"]

    def get_patient_obj(self):
        return get_object_or_404(
            Patient, external_id=self.kwargs["patient_external_id"]
        )

    def get_encounter_obj(self, external_id):
        return get_object_or_404(
            Encounter.objects.filter(patient=self.get_patient_obj()).select_related(
                "facility"
            ),
            external_id=external_id,
        )

    def get_parent_obj(self, external_id, encounter=None):
        parent = get_object_or_404(
            ImmunizationRecommendation.objects.filter(
                patient=self.get_patient_obj(), is_group=True
            ),
            external_id=external_id,
        )
        if parent.encounter_id and parent.encounter_id != getattr(
            encounter, "id", None
        ):
            raise ValidationError(
                "Parent recommendation belongs to a different encounter"
            )
        return parent

    def validate_data(self, instance, model_obj=None):
        if model_obj is not None:
            return
        if instance.patient != self.get_patient_obj().external_id:
            raise ValidationError("Patient does not match the patient in the URL")
        encounter = (
            self.get_encounter_obj(instance.encounter) if instance.encounter else None
        )
        if instance.parent:
            self.get_parent_obj(instance.parent, encounter)

    def authorize_write(self, patient, encounter=None):
        if encounter:
            allowed = AuthorizationController.call(
                "can_write_encounter_immunization_recommendation",
                self.request.user,
                encounter,
            )
        else:
            allowed = AuthorizationController.call(
                "can_write_patient_immunization_recommendation",
                self.request.user,
                patient,
            )
        if not allowed:
            raise PermissionDenied("Access denied to immunization recommendations")

    def authorize_create(self, instance):
        encounter = (
            self.get_encounter_obj(instance.encounter) if instance.encounter else None
        )
        self.authorize_write(self.get_patient_obj(), encounter)

    def authorize_update(self, request_obj, model_instance):
        self.authorize_write(model_instance.patient, model_instance.encounter)

    def authorize_retrieve(self, model_instance):
        if AuthorizationController.call(
            "can_read_patient_immunization_recommendation",
            self.request.user,
            model_instance.patient,
        ):
            return
        if model_instance.encounter and AuthorizationController.call(
            "can_read_encounter_immunization_recommendation",
            self.request.user,
            model_instance.encounter,
        ):
            return
        raise PermissionDenied("Access denied to immunization recommendations")

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .filter(patient__external_id=self.kwargs["patient_external_id"])
            .select_related("patient", "encounter", "parent")
        )
        encounter_id = self.request.query_params.get("encounter")
        encounter = self.get_encounter_obj(encounter_id) if encounter_id else None
        if encounter:
            queryset = queryset.filter(encounter=encounter)
        if self.action == "list" and not AuthorizationController.call(
            "can_read_patient_immunization_recommendation",
            self.request.user,
            self.get_patient_obj(),
        ):
            if not encounter:
                raise PermissionDenied("Access denied to immunization recommendations")
            if not AuthorizationController.call(
                "can_read_encounter_immunization_recommendation",
                self.request.user,
                encounter,
            ):
                raise PermissionDenied("Access denied to immunization recommendations")
        return queryset

    @extend_schema(
        request=ImmunizationPolicyApplySpec,
        responses={201: ImmunizationPolicyApplyResponseSpec},
    )
    @action(detail=False, methods=["POST"])
    def apply_policy(self, request, *args, **kwargs):
        """Create a policy's recommendation tree atomically.

        Template dates are day offsets from reference_date. An optional parent
        attaches the tree to an existing recommendation group for the patient.
        Returns every created node with a due forecast status.
        """
        data = ImmunizationPolicyApplySpec.model_validate(request.data)
        patient = self.get_patient_obj()
        encounter = self.get_encounter_obj(data.encounter) if data.encounter else None
        self.authorize_write(patient, encounter)
        parent = self.get_parent_obj(data.parent, encounter) if data.parent else None
        policy = get_object_or_404(
            ImmunizationPolicy.objects.select_related("facility"),
            external_id=data.policy,
        )
        if policy.facility_id:
            if not AuthorizationController.call(
                "can_list_facility_immunization_policy", request.user, policy.facility
            ):
                raise PermissionDenied("Access denied to immunization policy")
            if encounter and encounter.facility_id != policy.facility_id:
                raise ValidationError("Policy belongs to a different facility")

        template = ImmunizationPolicyTemplateSpec.model_validate(policy.policy_template)
        created = []
        date_fields = {"due_date", "earliest_date", "overdue_date"}

        def create_recommendations(node, parent):
            fields = node.model_dump(
                mode="json",
                exclude={"id", "meta", "children", *date_fields},
                exclude_defaults=True,
            )
            for field in date_fields:
                offset = getattr(node, field)
                if offset is not MISSING:
                    try:
                        fields[field] = data.reference_date + timedelta(days=offset)
                    except OverflowError as exc:
                        raise ValidationError(
                            "Policy date is outside the supported range"
                        ) from exc
            recommendation = ImmunizationRecommendation(
                **fields,
                patient=patient,
                encounter=encounter,
                parent=parent,
                forecast_status=ImmunizationRecommendationForecastStatus.due.value,
            )
            self.perform_create(recommendation)
            created.append(recommendation)
            for child in node.children:
                create_recommendations(child, recommendation)

        with transaction.atomic():
            create_recommendations(template, parent)
        return Response(
            [self.serialize_retrieve(instance) for instance in created],
            status=status.HTTP_201_CREATED,
        )
