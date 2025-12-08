from django_filters import rest_framework as filters
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
    EMRUpsertMixin,
)
from care.emr.models.observation_definition import ObservationDefinition
from care.emr.resources.observation_definition.spec import (
    ObservationDefinitionCreateSpec,
    ObservationDefinitionReadSpec,
    ObservationDefinitionUpdateSpec,
)
from care.facility.models import Facility
from care.security.authorization import AuthorizationController
from care.utils.registries.evaluation_metric import EvaluatorMetricsRegistry
from care.utils.shortcuts import get_object_or_404


class ObservationDefinitionFilters(filters.FilterSet):
    facility = filters.UUIDFilter(field_name="facility__external_id")
    category = filters.CharFilter(lookup_expr="iexact")
    status = filters.CharFilter(lookup_expr="iexact")
    title = filters.CharFilter(lookup_expr="icontains")


class ObservationDefinitionViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
    EMRUpsertMixin,
):
    lookup_field = "slug"
    database_model = ObservationDefinition
    pydantic_model = ObservationDefinitionCreateSpec
    pydantic_update_model = ObservationDefinitionUpdateSpec
    pydantic_read_model = ObservationDefinitionReadSpec
    filterset_class = ObservationDefinitionFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def recalculate_slug(self, instance):
        if instance.facility:
            instance.slug = ObservationDefinition.calculate_slug_from_facility(
                instance.facility.external_id, instance.slug
            )
        else:
            instance.slug = ObservationDefinition.calculate_slug_from_instance(
                instance.slug
            )

    def perform_create(self, instance):
        self.recalculate_slug(instance)
        super().perform_create(instance)

    def perform_update(self, instance):
        self.recalculate_slug(instance)
        return super().perform_update(instance)

    def validate_data(self, instance, model_obj=None):
        queryset = ObservationDefinition.objects.all()
        facility = None
        if model_obj:
            queryset = queryset.exclude(id=model_obj.id)
            facility = str(model_obj.facility.external_id)
        else:
            facility = instance.facility

        if facility:
            slug = ObservationDefinition.calculate_slug_from_facility(
                facility, instance.slug_value
            )
        else:
            slug = ObservationDefinition.calculate_slug_from_instance(
                instance.slug_value
            )

        queryset = queryset.filter(slug__iexact=slug)
        if queryset.exists():
            raise ValidationError("Slug already exists.")

        return super().validate_data(instance, model_obj)

    def authorize_create(self, instance):
        """
        Only superusers can create observation definitions that are not facility-specific.
        The user must have permission to create the observation definition in the facility.
        """
        if not instance.facility and not self.request.user.is_superuser:
            raise PermissionDenied("Access Denied to Observation Definition")
        if instance.facility and not AuthorizationController.call(
            "can_write_facility_observation_definition",
            self.request.user,
            get_object_or_404(Facility, external_id=instance.facility),
        ):
            raise PermissionDenied("Access Denied to Observation Definition")

    def authorize_update(self, request_obj, model_instance):
        """
        Only superusers can update observation definitions that are not facility-specific.
        The user must have permission to update the observation definition in the facility.
        """
        if not model_instance.facility and not self.request.user.is_superuser:
            raise PermissionDenied("Access Denied to Observation Definition")

        if model_instance.facility and not AuthorizationController.call(
            "can_write_facility_observation_definition",
            self.request.user,
            model_instance.facility,
        ):
            raise PermissionDenied("Access Denied to Observation Definition")

    def authorize_retrieve(self, model_instance):
        if not model_instance.facility:
            # All users can view non-facility specific observation definitions
            return
        if not AuthorizationController.call(
            "can_list_facility_observation_definition",
            self.request.user,
            model_instance.facility,
        ):
            raise PermissionDenied("Access Denied to Observation Definition")

    def get_queryset(self):
        """
        If no facility filters are applied, all objects must be returned without a facility filter.
        If facility filter is applied, check for read permission and return all inside facility.
        """
        base_queryset = super().get_queryset()
        if self.action in ["list"]:
            if "facility" in self.request.GET:
                facility_id = self.request.GET["facility"]
                facility_obj = get_object_or_404(Facility, external_id=facility_id)
                if not AuthorizationController.call(
                    "can_list_facility_observation_definition",
                    self.request.user,
                    facility_obj,
                ):
                    raise PermissionDenied("Access Denied to Observation Definition")
                return base_queryset.filter(facility=facility_obj)
            base_queryset = base_queryset.filter(facility__isnull=True)
        return base_queryset

    @action(detail=False, methods=["GET"])
    def metrics(self, request, *args, **kwargs):
        all_metrics = EvaluatorMetricsRegistry.get_all_metrics()
        response = []
        for metric in all_metrics:
            response.append(
                {
                    "name": metric.name,
                    "verbose_name": metric.verbose_name,
                    "context": metric.context,
                    "allowed_operations": metric.allowed_operations,
                }
            )
        return Response(response)
