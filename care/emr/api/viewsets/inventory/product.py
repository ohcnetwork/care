from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework.exceptions import ValidationError

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.emr.models.product import Product
from care.emr.resources.inventory.product.spec import ProductReadSpec, ProductWriteSpec
from care.facility.models.facility import Facility


class ProductFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    facility = filters.UUIDFilter(field_name="facility__external_id")
    product_knowledge = filters.UUIDFilter(field_name="product_knowledge__external_id")
    product_knowledge_name = filters.CharFilter(
        field_name="product_knowledge__name", lookup_expr="icontains"
    )


class ProductViewSet(
    EMRCreateMixin, EMRRetrieveMixin, EMRUpdateMixin, EMRListMixin, EMRBaseViewSet
):
    database_model = Product
    pydantic_model = ProductWriteSpec
    pydantic_read_model = ProductReadSpec
    filterset_class = ProductFilters
    filter_backends = [filters.DjangoFilterBackend]

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
        super().perform_create(instance)

    def get_queryset(self):
        return super().get_queryset().filter(facility=self.get_facility_obj())
