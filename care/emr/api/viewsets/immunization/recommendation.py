from django.db import transaction
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
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
from care.emr.models.immunisation import ImmunizationRecommendation
from care.emr.resources.favorites.filters import FavoritesFilter
from care.emr.resources.immunisation.recommendation import (
    ImmunizationRecommendationCreateSpec,
    ImmunizationRecommendationListSpec,
    ImmunizationRecommendationRetrieveSpec,
    ImmunizationRecommendationTreeCreateSpec,
    ImmunizationRecommendationUpdateSpec,
)
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404


class ImmunizationReccomendationFilters(filters.FilterSet):
    pass


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
    filterset_class = ImmunizationReccomendationFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter, FavoritesFilter]
    ordering_fields = ["created_date", "modified_date"]

    @extend_schema(
        request=ImmunizationRecommendationTreeCreateSpec,
        responses=ImmunizationRecommendationRetrieveSpec,
    )
    @action(detail=False, methods=["POST"])
    @transaction.atomic
    def create_tree(self, request, *args, **kwargs):
        data = ImmunizationRecommendationTreeCreateSpec.model_validate(request.data)
        if str(data.patient) != self.kwargs["patient_external_id"]:
            raise ValidationError("Patient does not match the requested patient")
        encounter = get_object_or_404(
            Encounter,
            external_id=data.encounter,
            patient__external_id=data.patient,
        )
        if not AuthorizationController.call(
            "can_update_encounter_clinical_data", request.user, encounter
        ):
            raise PermissionDenied("You do not have permission to update encounter")

        def create_node(node, parent=None):
            created = self.handle_create(
                {
                    **node.model_dump(mode="json", exclude={"children"}),
                    "patient": data.patient,
                    "encounter": data.encounter,
                    "parent": parent,
                    "forecast_status": "due",
                }
            )
            for child in node.children:
                create_node(child, created["id"])
            return created

        return Response(create_node(data.root))
