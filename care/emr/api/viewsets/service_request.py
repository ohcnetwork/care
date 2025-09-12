from django.db import transaction
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
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
from care.emr.models.activity_definition import ActivityDefinition
from care.emr.models.encounter import Encounter
from care.emr.models.location import FacilityLocation
from care.emr.models.organization import FacilityOrganizationUser
from care.emr.models.service_request import ServiceRequest
from care.emr.models.specimen_definition import SpecimenDefinition
from care.emr.registries.system_questionnaire.system_questionnaire import (
    InternalQuestionnaireRegistry,
)
from care.emr.resources.activity_definition.service_request import (
    apply_ad_charge_definitions,
    convert_ad_to_sr,
)
from care.emr.resources.questionnaire.spec import SubjectType
from care.emr.resources.service_request.spec import (
    ServiceRequestCreateSpec,
    ServiceRequestReadSpec,
    ServiceRequestRetrieveSpec,
    ServiceRequestUpdateSpec,
)
from care.emr.resources.specimen.spec import (
    BaseSpecimenSpec,
    SpecimenReadSpec,
    SpecimenUpdateSpec,
)
from care.emr.resources.specimen_definition.specimen import convert_sd_to_specimen
from care.emr.resources.tag.config_spec import TagResource
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404


class ServiceRequestFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    category = filters.CharFilter(lookup_expr="iexact")
    title = filters.CharFilter(lookup_expr="icontains")
    priority = filters.CharFilter(lookup_expr="iexact")
    intent = filters.CharFilter(lookup_expr="iexact")
    do_not_perform = filters.BooleanFilter()
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    patient = filters.UUIDFilter(field_name="patient__external_id")
    requester = filters.UUIDFilter(field_name="requester__external_id")


class ApplyActivityDefinitionRequest(BaseModel):
    activity_definition: str
    service_request: ServiceRequestUpdateSpec
    encounter: UUID4


class ApplySpecimenDefinitionRequest(BaseModel):
    specimen_definition: UUID4
    specimen: SpecimenUpdateSpec


class ServiceRequestViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRTagMixin,
    EMRBaseViewSet,
):
    database_model = ServiceRequest
    pydantic_model = ServiceRequestCreateSpec
    pydantic_update_model = ServiceRequestUpdateSpec
    pydantic_read_model = ServiceRequestReadSpec
    pydantic_retrieve_model = ServiceRequestRetrieveSpec
    filterset_class = ServiceRequestFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    questionnaire_type = "service_request"
    questionnaire_title = "Service Request"
    questionnaire_description = "Service Request"
    questionnaire_subject_type = SubjectType.patient.value
    resource_type = TagResource.service_request
    ordering_fields = ["created_date", "modified_date"]

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def convert_external_id_to_internal_id(self, instance):
        ids = []
        for location in instance._locations:  # noqa: SLF001
            obj = (
                FacilityLocation.objects.only("id")
                .filter(external_id=location, facility=self.get_facility_obj())
                .first()
            )
            if not obj:
                error_msg = f"Location with id {location} not found"
                raise ValidationError(error_msg)
            ids.append(obj.id)
        instance.locations = ids

    def validate_health_care_service(self, instance):
        if (
            instance.healthcare_service
            and instance.healthcare_service.facility != instance.facility
        ):
            raise ValidationError("Healthcare Service must be from the same facility")

    def validate_requester(self, instance, facility):
        if not FacilityOrganizationUser.objects.filter(
            organization__facility=facility, user=instance.requester
        ).exists():
            raise ValidationError("requester must be a member of the facility")

    def perform_create(self, instance):
        self.convert_external_id_to_internal_id(instance)
        instance.facility = self.get_facility_obj()
        self.validate_health_care_service(instance)
        self.validate_requester(instance, instance.facility)
        return super().perform_create(instance)

    def perform_update(self, instance):
        self.convert_external_id_to_internal_id(instance)
        self.validate_health_care_service(instance)
        return super().perform_update(instance)

    def authorize_create(self, instance):
        encounter = get_object_or_404(
            Encounter, external_id=instance.encounter, facility=self.get_facility_obj()
        )
        if not AuthorizationController.call(
            "can_write_service_request_in_encounter",
            self.request.user,
            encounter,
        ):
            raise PermissionDenied(
                "You do not have permission to create a service request for this encounter"
            )

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_write_service_request",
            self.request.user,
            model_instance,
        ):
            raise PermissionDenied(
                "You do not have permission to update this service request"
            )

    def authorize_retrieve(self, model_instance):
        """
        The user must have access to the location or encounter to access the SR
        """
        if not AuthorizationController.call(
            "can_read_service_request",
            self.request.user,
            model_instance,
        ):
            raise PermissionDenied(
                "You do not have permission to read this service request"
            )

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .filter(facility=self.get_facility_obj())
            .select_related("encounter", "encounter__patient")
        )
        if self.action != "list":
            return queryset  # Authz is handled separately
        if self.request.user.is_superuser:
            return queryset
        if "location" in self.request.GET:
            location = get_object_or_404(
                FacilityLocation, external_id=self.request.GET["location"]
            )
            if not AuthorizationController.call(
                "can_list_location_service_request",
                self.request.user,
                location,
            ):
                raise PermissionDenied(
                    "You do not have permission to view service requests for this location"
                )
            return queryset.filter(locations__overlap=[location.id])
        if "encounter" in self.request.GET:
            encounter = get_object_or_404(
                Encounter, external_id=self.request.GET["encounter"]
            )
            if not AuthorizationController.call(
                "can_view_service_request_for_encounter",
                self.request.user,
                encounter,
            ):
                raise PermissionDenied(
                    "You do not have permission to view service requests for this encounter"
                )
            return queryset.filter(encounter=encounter)
        raise ValidationError("Location or encounter is required")

    @extend_schema(
        request=ApplyActivityDefinitionRequest,
    )
    @action(methods=["POST"], detail=False)
    def apply_activity_definition(self, request, *args, **kwargs):
        facility = self.get_facility_obj()
        request_params = ApplyActivityDefinitionRequest(**request.data)
        # Authorize
        encounter = get_object_or_404(
            Encounter, external_id=request_params.encounter, facility=facility
        )
        activity_definition = get_object_or_404(
            ActivityDefinition,
            slug=request_params.activity_definition,
            facility=facility,
        )
        service_request = convert_ad_to_sr(activity_definition, encounter)
        self.authorize_update(None, service_request)
        serializer_obj = ServiceRequestUpdateSpec.model_validate(
            request_params.service_request.model_dump(mode="json")
        )
        model_instance = serializer_obj.de_serialize(obj=service_request)
        model_instance.activity_definition = activity_definition
        model_instance.created_by = self.request.user
        model_instance.updated_by = self.request.user
        with transaction.atomic():
            self.perform_update(model_instance)
            apply_ad_charge_definitions(activity_definition, encounter, model_instance)
        return Response(
            self.get_retrieve_pydantic_model().serialize(model_instance).to_json()
        )

    def authorize_create_specimen(self, service_request):
        if not AuthorizationController.call(
            "can_write_specimen",
            self.request.user,
            service_request,
        ):
            raise PermissionDenied(
                "You do not have permission to create a specimen for this encounter"
            )

    @extend_schema(
        request=BaseSpecimenSpec,
    )
    @action(methods=["POST"], detail=True)
    def create_specimen(self, request, *args, **kwargs):
        service_request = self.get_object()
        sepcimen_data = BaseSpecimenSpec(**request.data)
        self.authorize_create_specimen(service_request)
        model_instance = sepcimen_data.de_serialize()
        if not model_instance.accession_identifier:
            model_instance.accession_identifier = model_instance.external_id
        model_instance.patient = service_request.patient
        model_instance.encounter = service_request.encounter
        model_instance.facility = service_request.facility
        model_instance.service_request = service_request
        model_instance.created_by = self.request.user
        model_instance.updated_by = self.request.user
        model_instance.save()
        return Response(SpecimenReadSpec.serialize(model_instance).to_json())

    @extend_schema(
        request=ApplySpecimenDefinitionRequest,
    )
    @action(methods=["POST"], detail=True)
    def create_specimen_from_definition(self, request, *args, **kwargs):
        facility = self.get_facility_obj()
        service_request = self.get_object()
        request_params = ApplySpecimenDefinitionRequest(**request.data)
        # Authorize
        self.authorize_create_specimen(service_request)
        specimen_definition = get_object_or_404(
            SpecimenDefinition,
            external_id=request_params.specimen_definition,
            facility=facility,
        )
        specimen = convert_sd_to_specimen(specimen_definition)
        serializer_obj = SpecimenUpdateSpec.model_validate(
            request_params.specimen.model_dump(mode="json")
        )
        model_instance = serializer_obj.de_serialize(obj=specimen)
        if not model_instance.accession_identifier:
            model_instance.accession_identifier = model_instance.external_id
        model_instance.patient = service_request.patient
        model_instance.encounter = service_request.encounter
        model_instance.facility = service_request.facility
        model_instance.service_request = service_request
        model_instance.created_by = self.request.user
        model_instance.updated_by = self.request.user
        model_instance.save()
        return Response(SpecimenReadSpec.serialize(model_instance).to_json())


InternalQuestionnaireRegistry.register(ServiceRequestViewSet)
