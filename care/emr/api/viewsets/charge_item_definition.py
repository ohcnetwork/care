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
)
from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.resources.charge_item_definition.spec import (
    ChargeItemDefinitionReadSpec,
    ChargeItemDefinitionSpec,
)
from care.facility.models import Facility
from care.security.authorization.base import AuthorizationController


class ChargeItemDefinitionFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    title = filters.CharFilter(lookup_expr="icontains")


class ChargeItemDefinitionViewSet(
    EMRCreateMixin, EMRRetrieveMixin, EMRUpdateMixin, EMRListMixin, EMRBaseViewSet
):
    database_model = ChargeItemDefinition
    pydantic_model = ChargeItemDefinitionSpec
    pydantic_read_model = ChargeItemDefinitionReadSpec
    filterset_class = ChargeItemDefinitionFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def validate_data(self, instance, model_obj=None):
        queryset = ChargeItemDefinition.objects.filter(slug__exact=instance.slug)
        if model_obj:
            queryset = queryset.filter(facility=model_obj.facility).exclude(
                id=model_obj.id
            )
        else:
            queryset = queryset.filter(facility=self.get_facility_obj())
        if queryset.exists():
            raise ValidationError(
                "Charge Item Definition with this slug already exists."
            )
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
        base_queryset = self.database_model.objects.all()
        facility_obj = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_list_facility_charge_item_definition",
            self.request.user,
            facility_obj,
        ):
            raise PermissionDenied("Access Denied to Charge Item Definition")
        return base_queryset.filter(facility=facility_obj)
