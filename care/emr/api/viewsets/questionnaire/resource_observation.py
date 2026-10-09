from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel, Field
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelReadOnlyViewSet
from care.emr.api.viewsets.questionnaire.resource_authz import (
    authorize_resource_questionnaire_response_read,
    get_questionniare_resource,
)
from care.emr.models.facility_resource import FacilityResourceObservation
from care.emr.resources.common.coding import Coding
from care.emr.resources.observation.resource_spec import (
    ResourceObservationReadSpec,
    ResourceObservationRetrieveSpec,
)
from care.emr.resources.questionnaire.spec import QuestionType
from care.utils.filters.dummy_filter import DummyCharFilter, DummyUUIDFilter


class MultipleCodeFilter(filters.CharFilter):
    def filter(self, qs, value):
        queryset = qs
        if value:
            queryset = queryset.filter(main_code__code__in=value.split(","))
        return queryset


class IgnoreGroupFilter(filters.BooleanFilter):
    def filter(self, qs, value):
        if value:
            qs = qs.exclude(value_type=QuestionType.group.value)
        return qs


class ResourceObservationFilter(filters.FilterSet):
    codes = MultipleCodeFilter()
    ignore_group = IgnoreGroupFilter()
    subject_id = DummyUUIDFilter()
    subject_type = DummyCharFilter()


class ResourceObservationAnalyseRequest(BaseModel):
    codes: list[Coding] = Field(min_length=1, max_length=20)
    page_size: int = Field(10, le=30)


class ResourceObservationViewSet(EMRModelReadOnlyViewSet):
    database_model = FacilityResourceObservation
    pydantic_model = ResourceObservationReadSpec
    pydantic_retrieve_model = ResourceObservationRetrieveSpec
    filterset_class = ResourceObservationFilter
    filter_backends = [filters.DjangoFilterBackend]

    def get_queryset(self):
        queryset = super().get_queryset()
        subject_id = self.request.GET.get("subject_id")
        subject_type = self.request.GET.get("subject_type")
        if not subject_id or not subject_type:
            raise ValidationError("subject_id and subject_type are required")
        subject = get_questionniare_resource(subject_type, subject_id)
        authorize_resource_questionnaire_response_read(
            subject_type, subject, self.request.user
        )
        queryset = queryset.filter(subject_type=subject_type, subject_id=subject_id)

        return queryset.order_by("-modified_date")

    @extend_schema(
        request=ResourceObservationAnalyseRequest,
    )
    @action(methods=["POST"], detail=False)
    def analyse(self, request, **kwargs):
        request_params = ResourceObservationAnalyseRequest(**request.data)
        queryset = self.get_queryset()
        page_size = request_params.page_size
        results = []
        for code in request_params.codes:
            code_queryset = queryset.filter(
                main_code__code=code.code, main_code__system=code.system
            )[:page_size]
            code_results = [
                self.get_read_pydantic_model()
                .serialize(obj)
                .model_dump(exclude=["meta"])
                for obj in code_queryset
            ]
            results.append(
                {
                    "code": code.model_dump(exclude_defaults=True),
                    "results": code_results,
                }
            )
        return Response({"results": results})
