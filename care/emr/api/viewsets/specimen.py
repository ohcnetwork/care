from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel, field_validator
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRBaseViewSet, EMRRetrieveMixin, EMRUpdateMixin
from care.emr.models.specimen import Specimen
from care.emr.resources.specimen.spec import (
    BaseSpecimenSpec,
    SpecimenReadSpec,
    SpecimenRetrieveSpec,
    SpecimenUpdateSpec,
)
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404


class SpecimenFilters(filters.FilterSet):
    accession_identifier = filters.CharFilter(lookup_expr="icontains")


class SpecimenRetrieveByAccessionIdentifierSpec(BaseModel):
    accession_identifier: str

    @field_validator("accession_identifier")
    @classmethod
    def validate_accession_identifier(cls, v):
        if len(v) < 5:  # noqa PLR2004
            raise ValueError("Accession identifier must be at least 5 characters long")
        return v


class SpecimenViewSet(EMRRetrieveMixin, EMRUpdateMixin, EMRBaseViewSet):
    database_model = Specimen
    pydantic_model = BaseSpecimenSpec
    pydantic_update_model = SpecimenUpdateSpec
    pydantic_read_model = SpecimenReadSpec
    pydantic_retrieve_model = SpecimenRetrieveSpec
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]
    filterset_class = SpecimenFilters

    def authorize_update(self, request_obj, model_instance):
        service_request = model_instance.service_request
        if not AuthorizationController.call(
            "can_write_specimen",
            self.request.user,
            service_request,
        ):
            raise PermissionDenied("You do not have permission to write this specimen")

    def authorize_retrieve(self, model_instance):
        service_request = model_instance.service_request
        if not AuthorizationController.call(
            "can_read_specimen",
            self.request.user,
            service_request,
        ):
            raise PermissionDenied("You do not have permission to read this specimen")

    @extend_schema(
        request=SpecimenRetrieveByAccessionIdentifierSpec,
        responses={200: SpecimenRetrieveSpec},
    )
    @action(methods=["POST"], detail=False)
    def retrieve_by_accession_identifier(self, request, *args, **kwargs):
        accession_identifier = SpecimenRetrieveByAccessionIdentifierSpec(**request.data)
        try:
            specimen = get_object_or_404(
                Specimen, accession_identifier=accession_identifier.accession_identifier
            )
        except Specimen.MultipleObjectsReturned as e:
            raise ValidationError(
                "Multiple specimens found with the same accession identifier"
            ) from e
        except Specimen.DoesNotExist as e:
            raise ValidationError(
                "Specimen not found with the given accession identifier"
            ) from e
        if not AuthorizationController.call(
            "can_read_specimen",
            self.request.user,
            specimen.service_request,
        ):
            raise PermissionDenied("You do not have permission to read this specimen")
        return Response(SpecimenRetrieveSpec.serialize(specimen).to_json())
