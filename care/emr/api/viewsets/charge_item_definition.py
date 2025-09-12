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
from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.resource_category import ResourceCategory
from care.emr.resources.charge_item_definition.spec import (
    ChargeItemDefinitionReadSpec,
    ChargeItemDefinitionSpec,
)
from care.emr.resources.favorites.filters import FavoritesFilter
from care.emr.resources.favorites.spec import FavoriteResourceChoices
from care.facility.models import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.filters.dummy_filter import DummyBooleanFilter, DummyCharFilter
from care.utils.shortcuts import get_object_or_404


class ChargeItemDefinitionFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    title = filters.CharFilter(lookup_expr="icontains")
    category = DummyCharFilter()
    include_children = DummyBooleanFilter()


class ChargeItemDefinitionViewSet(
    EMRFavoritesMixin,
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRUpsertMixin,
    EMRBaseViewSet,
):
    lookup_field = "slug"
    database_model = ChargeItemDefinition
    pydantic_model = ChargeItemDefinitionSpec
    pydantic_read_model = ChargeItemDefinitionReadSpec
    filterset_class = ChargeItemDefinitionFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter, FavoritesFilter]
    ordering_fields = ["created_date", "modified_date"]
    FAVORITE_RESOURCE = FavoriteResourceChoices.charge_item_definition

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def get_serializer_create_context(self):
        facility = self.get_facility_obj()
        return {"facility": facility}

    def get_serializer_update_context(self):
        obj = self.get_object()
        return {"facility": obj.facility}

    def validate_data(self, instance, model_obj=None):
        facility = self.get_facility_obj() if not model_obj else model_obj.facility

        queryset = ChargeItemDefinition.objects.filter(
            slug__iexact=instance.slug, facility=facility
        )
        if model_obj:
            queryset = queryset.exclude(id=model_obj.id)

        if queryset.exists():
            raise ValidationError(
                "Charge Item Definition with this slug already exists."
            )
        if instance.category:
            get_object_or_404(
                ResourceCategory.objects.only("id"),
                slug=instance.category,
                facility=facility,
            )  # Exists Check
        return super().validate_data(instance, model_obj)

    def perform_create(self, instance):
        instance.facility = self.get_facility_obj()
        super().perform_create(instance)

    def authorize_create(self, instance):
        if not AuthorizationController.call(
            "can_write_facility_charge_item_definition",
            self.request.user,
            self.get_facility_obj(),
        ):
            raise PermissionDenied("Access Denied to Charge Item Definition")

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_write_facility_charge_item_definition",
            self.request.user,
            model_instance.facility,
        ):
            raise PermissionDenied("Access Denied to Charge Item Definition")

    def get_queryset(self):
        base_queryset = super().get_queryset().select_related("category")
        facility_obj = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_list_facility_charge_item_definition",
            self.request.user,
            facility_obj,
        ):
            raise PermissionDenied("Access Denied to Charge Item Definition")
        if self.action == "list" and self.request.GET.get("category"):
            category = get_object_or_404(
                ResourceCategory.objects.only("id"),
                slug=self.request.GET.get("category"),
                facility=facility_obj,
            )
            if self.request.GET.get("include_children", "False").lower() == "true":
                base_queryset = base_queryset.filter(
                    category__parent_cache__overlap=[category.id]
                )
            else:
                base_queryset = base_queryset.filter(category=category)
        return base_queryset.filter(facility=facility_obj)
