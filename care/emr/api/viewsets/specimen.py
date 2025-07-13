from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter

from care.emr.api.viewsets.base import EMRBaseViewSet, EMRRetrieveMixin, EMRUpdateMixin
from care.emr.models.specimen import Specimen
from care.emr.resources.specimen.spec import (
    BaseSpecimenSpec,
    SpecimenReadSpec,
    SpecimenRetrieveSpec,
    SpecimenUpdateSpec,
)
from care.security.authorization.base import AuthorizationController


class SpecimenFilters(filters.FilterSet):
    accession_identifier = filters.CharFilter(lookup_expr="icontains")


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
