from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRUpsertMixin,
)
from care.emr.models.resource_category import (
    ResourceCategory,
    summarise_monetary_components,
)
from care.emr.resources.common.monetary_component import (
    MonetaryComponentsWithoutBase,
    MonetaryComponentType,
)
from care.emr.resources.resource_category.spec import (
    ResourceCategoryReadSpec,
    ResourceCategoryResourceTypeOptions,
    ResourceCategoryUpdateSpec,
    ResourceCategoryWriteSpec,
)
from care.facility.models import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404


class ResourceCategoryFilters(filters.FilterSet):
    parent = filters.CharFilter(field_name="parent__slug", lookup_expr="iexact")
    title = filters.CharFilter(field_name="title", lookup_expr="icontains")
    resource_type = filters.CharFilter(field_name="resource_type", lookup_expr="iexact")
    resource_sub_type = filters.CharFilter(
        field_name="resource_sub_type", lookup_expr="iexact"
    )
    level_cache = filters.NumberFilter(field_name="level_cache")


class ResourceCategoryViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRUpsertMixin,
    EMRBaseViewSet,
):
    lookup_field = "slug"
    database_model = ResourceCategory
    pydantic_model = ResourceCategoryWriteSpec
    pydantic_update_model = ResourceCategoryUpdateSpec
    pydantic_read_model = ResourceCategoryReadSpec
    filterset_class = ResourceCategoryFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def validate_data(self, instance, model_obj=None):
        facility = self.get_facility_obj() if not model_obj else model_obj.facility

        queryset = ResourceCategory.objects.all()

        if model_obj:
            queryset = queryset.exclude(id=model_obj.id)

        facility_external_id = str(facility.external_id)
        slug = ResourceCategory.calculate_slug_from_facility(
            facility_external_id, instance.slug_value
        )

        queryset = queryset.filter(slug__iexact=slug)

        if queryset.exists():
            raise ValidationError(
                "Charge Item Definition with this slug already exists."
            )

        if not model_obj and instance.parent:
            parent = instance.parent
            if parent:
                parent = get_object_or_404(
                    ResourceCategory, slug=parent, facility=facility
                )
                if parent.resource_type != instance.resource_type:
                    raise ValidationError(
                        "Parent category does not belong to same resource type"
                    )
                if parent.is_child:
                    raise ValidationError("Parent category is a child")

    def perform_create(self, instance):
        instance.facility = self.get_facility_obj()
        instance.slug = ResourceCategory.calculate_slug_from_facility(
            instance.facility.external_id, instance.slug
        )
        super().perform_create(instance)

    def perform_update(self, instance):
        instance.slug = ResourceCategory.calculate_slug_from_facility(
            instance.facility.external_id, instance.slug
        )
        super().perform_update(instance)

    def authorize_create(self, instance):
        if not AuthorizationController.call(
            "can_write_facility_resource_category",
            self.request.user,
            self.get_facility_obj(),
        ):
            raise PermissionDenied("Access Denied to Charge Item Definition Category")

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_write_facility_resource_category",
            self.request.user,
            model_instance.facility,
        ):
            raise PermissionDenied("Access Denied to Charge Item Definition Category")

    def get_queryset(self):
        queryset = super().get_queryset()
        facility_obj = self.get_facility_obj()
        if "parent" in self.request.GET and not self.request.GET.get("parent"):
            queryset = queryset.filter(parent__isnull=True)
        if not AuthorizationController.call(
            "can_list_facility_resource_category",
            self.request.user,
            facility_obj,
        ):
            raise PermissionDenied("Access Denied to Charge Item Definition Category")
        return queryset.filter(facility=facility_obj)

    @action(detail=True, methods=["POST"])
    def set_monetary_components(self, request, *args, **kwargs):
        obj = self.get_object()
        if (
            obj.resource_type
            != ResourceCategoryResourceTypeOptions.charge_item_definition.value
        ):
            raise ValidationError("Resource category is not a charge item definition")

        self.authorize_update(None, obj)
        monetary_components = MonetaryComponentsWithoutBase.model_validate(request.data)
        for component in monetary_components:
            if component.monetary_component_type == MonetaryComponentType.base.value:
                raise ValidationError(
                    "Base component is not allowed in configured monetary components"
                )
        obj.configured_monetary_components = monetary_components.model_dump(
            mode="json", exclude_defaults=True
        )
        obj.save()
        summarise_monetary_components(obj.id)
        obj = self.get_object()  # Refresh object to get updated fields
        return Response(self.get_retrieve_pydantic_model().serialize(obj).to_json())
