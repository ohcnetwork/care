from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRUpsertMixin,
)
from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.resources.inventory.product_knowledge.spec import (
    BaseProductKnowledgeSpec,
    ProductKnowledgeReadSpec,
    ProductKnowledgeWriteSpec,
)
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.filters.null_filter import NullFilter


class ProductKnowledgeFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    facility = filters.UUIDFilter(field_name="facility__external_id")
    name = filters.CharFilter(lookup_expr="icontains")  # TODO : Need better searching
    product_type = filters.CharFilter(lookup_expr="iexact")
    facility_is_null = NullFilter(field_name="facility")


class ProductKnowledgeViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
    EMRUpsertMixin,
):
    database_model = ProductKnowledge
    pydantic_model = ProductKnowledgeWriteSpec
    pydantic_update_model = BaseProductKnowledgeSpec
    pydantic_read_model = ProductKnowledgeReadSpec
    filterset_class = ProductKnowledgeFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def authorize_create(self, instance):
        if instance.facility:
            facility = get_object_or_404(Facility, external_id=instance.facility)
            if not AuthorizationController.call(
                "can_write_facility_product_knowledge",
                self.request.user,
                facility,
            ):
                raise PermissionDenied("Cannot create product knowledge")
        elif not self.request.user.is_superuser:
            raise PermissionDenied("Cannot create product knowledge")

    def authorize_update(self, request_obj, model_instance):
        if model_instance.facility:
            if not AuthorizationController.call(
                "can_write_facility_product_knowledge",
                self.request.user,
                model_instance.facility,
            ):
                raise PermissionDenied("Cannot update product knowledge")
        elif not self.request.user.is_superuser:
            raise PermissionDenied("Cannot update product knowledge")
        return super().authorize_update(request_obj, model_instance)

    def authorize_retrieve(self, model_instance):
        if model_instance.facility and not AuthorizationController.call(
            "can_list_facility_product_knowledge",
            self.request.user,
            model_instance.facility,
        ):
            raise PermissionDenied("Cannot read product knowledge")

    def get_queryset(self):
        if self.action != "list":
            return super().get_queryset()
        if "facility" in self.request.GET:
            facility = get_object_or_404(
                Facility, external_id=self.request.GET["facility"]
            )
            if not AuthorizationController.call(
                "can_list_facility_product_knowledge",
                self.request.user,
                facility,
            ):
                raise PermissionDenied("Cannot read product knowledge")
            return ProductKnowledge.objects.filter(facility=facility)
        return super().get_queryset()
