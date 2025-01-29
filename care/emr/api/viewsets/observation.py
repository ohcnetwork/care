from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel, Field
from rest_framework.decorators import action
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelReadOnlyViewSet
from care.emr.api.viewsets.encounter_authz_base import EncounterBasedAuthorizationBase
from care.emr.models.observation import Observation
from care.emr.resources.common.coding import Coding
from care.emr.resources.observation.spec import ObservationReadSpec
from care.emr.resources.questionnaire.spec import QuestionType


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


class ObservationFilter(filters.FilterSet):
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    codes = MultipleCodeFilter()
    ignore_group = IgnoreGroupFilter()


class ObservationAnalyseRequest(BaseModel):
    codes: list[Coding] = Field(min_length=1, max_length=20)
    page_size: int = Field(10, le=30)


class ObservationViewSet(EncounterBasedAuthorizationBase, EMRModelReadOnlyViewSet):
    database_model = Observation
    pydantic_model = ObservationReadSpec
    filterset_class = ObservationFilter
    filter_backends = [filters.DjangoFilterBackend]

    def get_queryset(self):
        self.authorize_read_encounter()

        queryset = (
            super()
            .get_queryset()
            .filter(patient__external_id=self.kwargs["patient_external_id"])
            .select_related("created_by", "updated_by", "data_entered_by")
        )

        return queryset.order_by("-modified_date")

    @extend_schema(
        request=ObservationAnalyseRequest,
    )
    @action(methods=["POST"], detail=False)
    def analyse(self, request, **kwargs):
        request_params = ObservationAnalyseRequest(**request.data)
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
