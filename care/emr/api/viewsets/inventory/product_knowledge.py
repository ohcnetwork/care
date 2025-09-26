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
from care.emr.api.viewsets.favorites import EMRFavoritesMixin
from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.models.resource_category import ResourceCategory
from care.emr.resources.favorites.filters import FavoritesFilter
from care.emr.resources.favorites.spec import FavoriteResourceChoices
from care.emr.resources.inventory.product_knowledge.spec import (
    ProductKnowledgeReadSpec,
    ProductKnowledgeUpdateSpec,
    ProductKnowledgeWriteSpec,
)
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.filters.dummy_filter import DummyBooleanFilter, DummyCharFilter
from care.utils.filters.null_filter import NullFilter
from care.utils.shortcuts import get_object_or_404


class ProductKnowledgeFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    facility = filters.UUIDFilter(field_name="facility__external_id")
    name = filters.CharFilter(lookup_expr="icontains")  # TODO : Need better searching
    product_type = filters.CharFilter(lookup_expr="iexact")
    facility_is_null = NullFilter(field_name="facility")
    alternate_identifier = filters.CharFilter(lookup_expr="iexact")
    category = DummyCharFilter()
    include_children = DummyBooleanFilter()


class ProductKnowledgeViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
    EMRUpsertMixin,
    EMRFavoritesMixin,
):
    lookup_field = "slug"
    database_model = ProductKnowledge
    pydantic_model = ProductKnowledgeWriteSpec
    pydantic_update_model = ProductKnowledgeUpdateSpec
    pydantic_read_model = ProductKnowledgeReadSpec
    filterset_class = ProductKnowledgeFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter, FavoritesFilter]
    ordering_fields = ["created_date", "modified_date"]
    FAVORITE_RESOURCE = FavoriteResourceChoices.product_knowledge.value

    def recalculate_slug(self, instance):
        if instance.facility:
            instance.slug = ProductKnowledge.calculate_slug_from_facility(
                instance.facility.external_id, instance.slug
            )
        else:
            instance.slug = ProductKnowledge.calculate_slug_from_instance(instance.slug)

    def perform_create(self, instance):
        self.recalculate_slug(instance)
        super().perform_create(instance)

    def perform_update(self, instance):
        self.recalculate_slug(instance)
        return super().perform_update(instance)

    def validate_data(self, instance, model_obj=None):
        queryset = ProductKnowledge.objects.all()
        facility = None
        if model_obj:
            queryset = queryset.exclude(id=model_obj.id)
            facility = (
                str(model_obj.facility.external_id) if model_obj.facility else None
            )
        else:
            facility = instance.facility

        if facility:
            slug = ProductKnowledge.calculate_slug_from_facility(
                facility, instance.slug_value
            )
        else:
            slug = ProductKnowledge.calculate_slug_from_instance(instance.slug_value)

        queryset = queryset.filter(slug__iexact=slug)
        if queryset.exists():
            raise ValidationError("Slug already exists.")

        if instance.category and facility:
            get_object_or_404(
                ResourceCategory.objects.only("id"), slug=instance.category
            )

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

    def get_queryset(self):
        queryset = super().get_queryset()
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

            queryset = queryset.filter(facility=facility)
            if self.request.GET.get("category"):
                category = get_object_or_404(
                    ResourceCategory.objects.only("id"),
                    slug=self.request.GET.get("category"),
                    facility=facility,
                )
                if self.request.GET.get("include_children", "False").lower() == "true":
                    queryset = queryset.filter(
                        category__parent_cache__overlap=[category.id]
                    )
                else:
                    queryset = queryset.filter(category=category)
        elif self.action == "list" and "facility" not in self.request.GET:
            queryset = queryset.filter(facility__isnull=True)
        return queryset
