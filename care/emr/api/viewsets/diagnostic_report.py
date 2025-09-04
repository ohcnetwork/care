from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.emr.models.diagnostic_report import DiagnosticReport
from care.emr.models.encounter import Encounter
from care.emr.models.observation import Observation
from care.emr.models.observation_definition import ObservationDefinition
from care.emr.models.patient import Patient
from care.emr.models.service_request import ServiceRequest
from care.emr.resources.diagnostic_report.spec import (
    DiagnosticReportCreateSpec,
    DiagnosticReportListSpec,
    DiagnosticReportRetrieveSpec,
    DiagnosticReportStatusChoices,
    DiagnosticReportUpdateSpec,
)
from care.emr.resources.observation.spec import ObservationUpdateSpec
from care.emr.resources.observation_definition.observation import (
    convert_od_to_observation,
)
from care.emr.resources.questionnaire.spec import SubjectType
from care.emr.utils.compute_observation_interpretation import (
    compute_observation_interpretation,
)
from care.security.authorization.base import AuthorizationController


class ApplyObservationDefinitionRequest(BaseModel):
    observation_definition: UUID4
    observation: ObservationUpdateSpec


class UpsertObservationRequest(BaseModel):
    observation: ObservationUpdateSpec
    observation_id: UUID4 | None = None
    observation_definition: UUID4 | None = None


class BatchUpdateObservationRequest(BaseModel):
    observations: list[UpsertObservationRequest]


class DiagnosticReportFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")


class DiagnosticReportViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
):
    database_model = DiagnosticReport
    pydantic_model = DiagnosticReportCreateSpec
    pydantic_update_model = DiagnosticReportUpdateSpec
    pydantic_read_model = DiagnosticReportListSpec
    pydantic_retrieve_model = DiagnosticReportRetrieveSpec
    filterset_class = DiagnosticReportFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def get_patient_obj(self):
        return get_object_or_404(
            Patient, external_id=self.kwargs["patient_external_id"]
        )

    def perform_create(self, instance):
        instance.patient = self.get_patient_obj()
        instance.encounter = instance.service_request.encounter
        instance.facility = instance.encounter.facility
        if instance.service_request.patient != instance.patient:
            raise ValidationError("Invalid Request")
        return super().perform_create(instance)

    def authorize_create(self, instance):
        if not AuthorizationController.call(
            "can_write_diagnostic_report",
            self.request.user,
            get_object_or_404(ServiceRequest, external_id=instance.service_request),
        ):
            raise ValidationError(
                "You do not have permission to write this diagnostic report"
            )

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_write_diagnostic_report",
            self.request.user,
            model_instance.service_request,
        ):
            raise ValidationError(
                "You do not have permission to write this diagnostic report"
            )

    def authorize_retrieve(self, model_instance):
        if AuthorizationController.call(
            "can_read_diagnostic_report",
            self.request.user,
            model_instance.service_request,
        ):
            return
        raise ValidationError(
            "You do not have permission to write this diagnostic report"
        )

    def get_queryset(self):
        queryset = super().get_queryset().filter(patient=self.get_patient_obj())
        if self.action != "list":
            return queryset  # Authz is handled separately
        if self.request.user.is_superuser:
            return queryset
        if self.request.GET.get("encounter"):
            encounter = get_object_or_404(
                Encounter, external_id=self.request.GET.get("encounter")
            )
            if AuthorizationController.call(
                "can_read_diagnostic_report_in_encounter",
                self.request.user,
                encounter,
            ):
                return queryset.filter(encounter=encounter)
        elif self.request.GET.get("service_request"):
            service_request = get_object_or_404(
                ServiceRequest, external_id=self.request.GET.get("service_request")
            )
            if AuthorizationController.call(
                "can_read_diagnostic_report",
                self.request.user,
                service_request,
            ):
                return queryset.filter(service_request=service_request)
        raise ValidationError("Service Request or encounter is required")

    @extend_schema(
        request=BatchUpdateObservationRequest,
    )
    @action(detail=True, methods=["POST"])
    def upsert_observations(self, request, *args, **kwargs):
        """
        Create observation from observation definition, from scratch or update existing observation
        """
        request_params = BatchUpdateObservationRequest(**request.data)
        diagnostic_report = self.get_object()
        if diagnostic_report.status in DiagnosticReportStatusChoices.final.value:
            raise ValidationError(
                "Cannot update observations for a final diagnostic report"
            )
        self.authorize_update({}, diagnostic_report)
        for request_param in request_params.observations:
            if request_param.observation_definition:
                observation_definition = get_object_or_404(
                    ObservationDefinition,
                    external_id=request_param.observation_definition,
                    facility=diagnostic_report.facility,
                )
                observation_obj = convert_od_to_observation(
                    observation_definition, diagnostic_report.encounter
                )
                serializer_obj = ObservationUpdateSpec.model_validate(
                    request_param.observation.model_dump(mode="json")
                )
                model_instance = serializer_obj.de_serialize(obj=observation_obj)
                model_instance.observation_definition = observation_definition
                model_instance.created_by = self.request.user
            elif request_param.observation_id:
                observation = get_object_or_404(
                    Observation,
                    external_id=request_param.observation_id,
                    diagnostic_report=diagnostic_report,
                )
                serializer_obj = ObservationUpdateSpec.model_validate(
                    request_param.observation.model_dump(mode="json")
                )
                model_instance = serializer_obj.de_serialize(obj=observation)
                model_instance.updated_by = self.request.user
            else:
                observation_obj = Observation()
                serializer_obj = ObservationUpdateSpec.model_validate(
                    request_param.observation.model_dump(mode="json")
                )
                model_instance = serializer_obj.de_serialize(obj=observation_obj)
                model_instance.created_by = self.request.user
            model_instance.updated_by = self.request.user
            model_instance.encounter = diagnostic_report.encounter
            model_instance.patient = diagnostic_report.patient
            model_instance.subject_id = diagnostic_report.encounter.external_id
            model_instance.diagnostic_report = diagnostic_report
            model_instance.subject_type = SubjectType.encounter.value

            # Compute interpretation if observation_definition is linked
            if model_instance.observation_definition:
                compute_observation_interpretation(model_instance)
            model_instance.save()
        return Response({"message": "Observations updated successfully"})
