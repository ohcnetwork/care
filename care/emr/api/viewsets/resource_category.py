from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.generics import get_object_or_404

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRUpsertMixin,
)
from care.emr.models.resource_category import ResourceCategory
from care.emr.resources.resource_category.spec import (
    ResourceCategoryBaseSpec,
    ResourceCategoryReadSpec,
    ResourceCategoryWriteSpec,
)
from care.facility.models import Facility
from care.security.authorization.base import AuthorizationController


class ResourceCategoryFilters(filters.FilterSet):
    parent = filters.UUIDFilter(field_name="parent__slug")
    title = filters.CharFilter(field_name="title", lookup_expr="icontains")
    resource_type = filters.CharFilter(field_name="resource_type", lookup_expr="iexact")
    resource_sub_type = filters.CharFilter(
        field_name="resource_sub_type", lookup_expr="iexact"
    )


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
    pydantic_update_model = ResourceCategoryBaseSpec
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
        queryset = ResourceCategory.objects.filter(
            slug__iexact=instance.slug, facility=facility
        )
        if model_obj:
            queryset = queryset.exclude(id=model_obj.id)
        if queryset.exists():
            raise ValidationError("Category with this slug already exists")
        if not model_obj and instance.parent:
            parent = instance.parent
            if parent:
                parent = get_object_or_404(ResourceCategory, slug=parent)
                if parent.facility != facility:
                    raise ValidationError("Parent category does not belong to facility")
                if parent.resource_type != instance.resource_type:
                    raise ValidationError(
                        "Parent category does not belong to same resource type"
                    )
                if parent.is_child:
                    raise ValidationError("Parent category is a child")

    def perform_create(self, instance):
        instance.facility = self.get_facility_obj()
        super().perform_create(instance)

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
        base_queryset = super().get_queryset()
        facility_obj = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_list_facility_resource_category",
            self.request.user,
            facility_obj,
        ):
            raise PermissionDenied("Access Denied to Charge Item Definition Category")
        return base_queryset.filter(facility=facility_obj)
