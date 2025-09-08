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
from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.models.resource_category import ResourceCategory
from care.emr.resources.inventory.product_knowledge.spec import (
    ProductKnowledgeReadSpec,
    ProductKnowledgeUpdateSpec,
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
    alternate_identifier = filters.CharFilter(lookup_expr="iexact")


class ProductKnowledgeViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
    EMRUpsertMixin,
):
    lookup_field = "slug"
    database_model = ProductKnowledge
    pydantic_model = ProductKnowledgeWriteSpec
    pydantic_update_model = ProductKnowledgeUpdateSpec
    pydantic_read_model = ProductKnowledgeReadSpec
    filterset_class = ProductKnowledgeFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def validate_data(self, instance, model_obj=None):
        queryset = ProductKnowledge.objects.filter(slug__iexact=instance.slug)
        if model_obj:
            facility = model_obj.facility.external_id
            if getattr(model_obj, "facility", None):
                queryset = queryset.filter(facility=model_obj.facility_id).exclude(
                    id=model_obj.id
                )
            else:
                queryset = queryset.filter(facility__isnull=True).exclude(
                    id=model_obj.id
                )
        elif instance.facility:
            facility = instance.facility
            queryset = queryset.filter(facility__external_id=instance.facility)
        else:
            queryset = queryset.filter(facility__isnull=True)
        if queryset.exists():
            raise ValidationError("Slug already exists.")

        if instance.category:
            category = get_object_or_404(ResourceCategory, slug=instance.category)
            if category.facility.external_id != facility:
                raise ValidationError("Category does not belong to facility")

        return super().validate_data(instance, model_obj)

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

    def get_object(self):
        queryset = self.get_queryset()
        try:
            if "facility" not in self.request.GET:
                return get_object_or_404(
                    queryset,
                    slug=self.kwargs["slug"],
                    facility__isnull=True,
                )
            facility = get_object_or_404(
                Facility.objects.only("id"), external_id=self.request.GET["facility"]
            )
            return get_object_or_404(
                queryset,
                slug=self.kwargs["slug"],
                facility=facility,
            )
        except ProductKnowledge.MultipleObjectsReturned:
            raise ValidationError("Multiple product knowledge with this slug found")

    def get_queryset(self):
        if self.action == "list" and "facility" in self.request.GET:
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
