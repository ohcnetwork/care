from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRUpsertMixin,
)
from care.emr.models.product import Product
from care.emr.resources.inventory.product.spec import ProductReadSpec, ProductWriteSpec
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController


class ProductFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    facility = filters.UUIDFilter(field_name="facility__external_id")
    product_knowledge = filters.UUIDFilter(field_name="product_knowledge__external_id")


class ProductViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRUpsertMixin,
    EMRBaseViewSet,
):
    database_model = Product
    pydantic_model = ProductWriteSpec
    pydantic_read_model = ProductReadSpec
    filterset_class = ProductFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def perform_create(self, instance):
        instance.facility = self.get_facility_obj()
        if (
            instance.charge_item_definition
            and instance.charge_item_definition.facility != instance.facility
        ):
            raise ValidationError("Invalid Charge Item")
        if (
            instance.product_knowledge
            and instance.product_knowledge.facility
            and instance.product_knowledge.facility != instance.facility
        ):
            raise ValidationError("Invalid Product Knowledge")
        super().perform_create(instance)

    def authorize_create(self, instance):
        facility = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_write_facility_product", self.request.user, facility
        ):
            raise PermissionDenied("Cannot write product")

    def authorize_update(self, request_obj, model_instance):
        return self.authorize_create(model_instance)

    def get_queryset(self):
        facility = self.get_facility_obj()
        queryset = super().get_queryset().filter(facility=facility)
        if self.action in ["list", "retrieve"] and not AuthorizationController.call(
            "can_list_facility_product", self.request.user, facility
        ):
            raise PermissionDenied("Cannot list products")
        return queryset
