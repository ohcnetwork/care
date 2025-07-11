from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.generics import get_object_or_404

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRTagMixin,
    EMRUpdateMixin,
)
from care.emr.models import ActivityDefinition
from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.location import FacilityLocation
from care.emr.models.observation_definition import ObservationDefinition
from care.emr.models.specimen_definition import SpecimenDefinition
from care.emr.resources.activity_definition.spec import (
    ActivityDefinitionReadSpec,
    ActivityDefinitionRetrieveSpec,
    ActivityDefinitionWriteSpec,
)
from care.emr.resources.tag.config_spec import TagResource
from care.facility.models import Facility
from care.security.authorization import AuthorizationController


class ActivityDefinitionFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    title = filters.CharFilter(lookup_expr="icontains")
    category = filters.CharFilter(lookup_expr="iexact")
    kind = filters.CharFilter(lookup_expr="iexact")


class ActivityDefinitionViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRTagMixin,
    EMRBaseViewSet,
):
    database_model = ActivityDefinition
    pydantic_model = ActivityDefinitionWriteSpec
    pydantic_read_model = ActivityDefinitionReadSpec
    pydantic_retrieve_model = ActivityDefinitionRetrieveSpec
    filterset_class = ActivityDefinitionFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]
    resource_type = TagResource.activity_definition

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def convert_external_id_to_internal_id(self, instance):
        # Convert speciment requirements to list of ids
        ids = []
        for specimen_requirement in instance.specimen_requirements:
            obj = (
                SpecimenDefinition.objects.only("id")
                .filter(external_id=specimen_requirement, facility=instance.facility)
                .first()
            )
            if not obj:
                error_msg = (
                    f"Specimen Definition with id {specimen_requirement} not found"
                )
                raise ValidationError(error_msg)
            ids.append(obj.id)
        instance.specimen_requirements = ids
        # Convert observation results into list of ids
        ids = []
        for observation_result in instance.observation_result_requirements:
            obj = (
                ObservationDefinition.objects.only("id")
                .filter(external_id=observation_result, facility=instance.facility)
                .first()
            )
            if not obj:
                error_msg = (
                    f"Observation Definition with id {observation_result} not found"
                )
                raise ValidationError(error_msg)
            ids.append(obj.id)
        instance.observation_result_requirements = ids
        # Convert locations into list of ids
        ids = []
        # AuthZ is fine because only administrators can create activity definitions
        # Administrators should be able to create location associations.
        for location in instance.locations:
            obj = (
                FacilityLocation.objects.only("id")
                .filter(external_id=location, facility=instance.facility)
                .first()
            )
            if not obj:
                error_msg = f"Location with id {location} not found"
                raise ValidationError(error_msg)
            ids.append(obj.id)
        instance.locations = ids

        ids = []
        for charge_item_definition in instance.charge_item_definitions:
            obj = (
                ChargeItemDefinition.objects.only("id")
                .filter(external_id=charge_item_definition, facility=instance.facility)
                .first()
            )
            if not obj:
                error_msg = (
                    f"Charge Item Definition with id {charge_item_definition} not found"
                )
                raise ValidationError(error_msg)
            ids.append(obj.id)
        instance.charge_item_definitions = ids

    def validate_health_care_service(self, instance):
        if (
            instance.healthcare_service
            and instance.healthcare_service.facility != instance.facility
        ):
            raise ValidationError("Healthcare Service must be from the same facility")

    def perform_create(self, instance):
        instance.facility = self.get_facility_obj()
        if ActivityDefinition.objects.filter(
            slug__iexact=instance.slug, facility=instance.facility
        ).exists():
            raise ValidationError("Activity Definition with this slug already exists.")
        self.convert_external_id_to_internal_id(instance)
        self.validate_health_care_service(instance)
        super().perform_create(instance)

    def perform_update(self, instance):
        self.convert_external_id_to_internal_id(instance)
        self.validate_health_care_service(instance)
        super().perform_update(instance)

    def authorize_create(self, instance):
        """
        The user must have permission to create activity definition in the facility.
        """
        facility = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_write_facility_activity_definition",
            self.request.user,
            facility,
        ):
            raise PermissionDenied("Access Denied to Activity Definition")

    def authorize_update(self, request_obj, model_instance):
        self.authorize_create(model_instance)

    def get_queryset(self):
        """
        If no facility filters are applied, all objects must be returned without a facility filter.
        If facility filter is applied, check for read permission and return all inside facility.
        """
        base_queryset = super().get_queryset()
        facility_obj = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_list_facility_activity_definition",
            self.request.user,
            facility_obj,
        ):
            raise PermissionDenied("Access Denied to Activity Definition")
        return base_queryset.filter(facility=facility_obj)
