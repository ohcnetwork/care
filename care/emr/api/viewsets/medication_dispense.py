from django.db import transaction
from django.db.models import Count, Q
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
from care.emr.models.encounter import Encounter
from care.emr.models.location import FacilityLocation
from care.emr.models.medication_dispense import MedicationDispense
from care.emr.resources.charge_item.apply_charge_item_definition import (
    apply_charge_item_definition,
)
from care.emr.resources.charge_item.handle_charge_item_cancel import (
    handle_charge_item_cancel,
)
from care.emr.resources.charge_item.spec import (
    ChargeItemResourceOptions,
    ChargeItemStatusOptions,
)
from care.emr.resources.encounter.spec import EncounterListSpec
from care.emr.resources.inventory.inventory_item.sync_inventory_item import (
    sync_inventory_item,
)
from care.emr.resources.medication.dispense.spec import (
    MEDICATION_DISPENSE_CANCELLED_STATUSES,
    MedicationDispenseReadSpec,
    MedicationDispenseUpdateSpec,
    MedicationDispenseWriteSpec,
)
from care.emr.resources.medication.request.spec import MedicationRequestDispenseStatus
from care.security.authorization.base import AuthorizationController
from care.utils.filters.dummy_filter import DummyBooleanFilter
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.shortcuts import get_object_or_404


class MedicationDispenseFilters(filters.FilterSet):
    status = MultiSelectFilter(field_name="status")
    category = filters.CharFilter(lookup_expr="iexact")
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    patient = filters.UUIDFilter(field_name="patient__external_id")
    item = filters.UUIDFilter(field_name="item__external_id")
    authorizing_prescription = filters.UUIDFilter(
        field_name="authorizing_request__prescription__external_id"
    )
    authorizing_request = filters.UUIDFilter(
        field_name="authorizing_request__external_id"
    )

    exclude_status = MultiSelectFilter(field_name="status", exclude=True)
    location = filters.UUIDFilter(field_name="location__external_id")
    include_children = DummyBooleanFilter()


class MedicationDispenseViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRUpsertMixin,
    EMRBaseViewSet,
):
    database_model = MedicationDispense
    pydantic_model = MedicationDispenseWriteSpec
    pydantic_update_model = MedicationDispenseUpdateSpec
    pydantic_read_model = MedicationDispenseReadSpec
    filterset_class = MedicationDispenseFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def perform_create(self, instance):
        with transaction.atomic():
            super().perform_create(instance)
            if instance.item.product.charge_item_definition:
                charge_item = apply_charge_item_definition(
                    instance.item.product.charge_item_definition,
                    instance.patient,
                    instance.encounter.facility,
                    encounter=instance.encounter,
                    quantity=instance.quantity,
                )
                charge_item.service_resource = (
                    ChargeItemResourceOptions.medication_dispense.value
                )
                charge_item.service_resource_id = str(instance.external_id)
                charge_item.save()
                instance.charge_item = charge_item
                instance.save(update_fields=["charge_item"])
            sync_inventory_item(instance.item.location, instance.item.product)
            if instance._fully_dispensed is not None and instance.authorizing_request:  # noqa
                if instance._fully_dispensed:  # noqa
                    instance.authorizing_request.dispense_status = (
                        MedicationRequestDispenseStatus.complete.value
                    )
                else:
                    instance.authorizing_request.dispense_status = (
                        MedicationRequestDispenseStatus.partial.value
                    )
                instance.authorizing_request.save()

    def authorize_location_write(self, location):
        if not AuthorizationController.call(
            "can_write_location_medication_dispense", self.request.user, location
        ):
            raise PermissionDenied(
                "You do not have permission to write medication dispenses"
            )

    def authorize_create(self, instance):
        """
        Creates only require permission to the location as the pharmacist will likely
        not have access to the encounter
        """
        location = instance.location
        location_obj = get_object_or_404(FacilityLocation, external_id=location)
        self.authorize_location_write(location_obj)

    def authorize_update(self, request_obj, model_instance):
        self.authorize_location_write(model_instance.location)

    def authorize_retrieve(self, model_instance):
        if not AuthorizationController.call(
            "can_list_location_medication_dispense",
            self.request.user,
            model_instance.location,
        ) and not AuthorizationController.call(
            "can_view_medication_dispense_for_encounter",
            self.request.user,
            model_instance.encounter,
        ):
            raise PermissionDenied(
                "You do not have permission to read medication dispense"
            )

    def validate_data(self, instance, model_obj=None):
        if model_obj and model_obj.status in MEDICATION_DISPENSE_CANCELLED_STATUSES:
            raise ValidationError("No updates allowed on cancelled medication dispense")
        return super().validate_data(instance, model_obj)

    def perform_update(self, instance):
        with transaction.atomic():
            current_obj = MedicationDispense.objects.get(id=instance.id)
            if (
                current_obj.status != instance.status
                and instance.status in MEDICATION_DISPENSE_CANCELLED_STATUSES
            ) and instance.charge_item:
                # Perform Cancellation of charge items as well
                handle_charge_item_cancel(instance.charge_item)
                instance.charge_item.status = ChargeItemStatusOptions.aborted.value
                instance.charge_item.save()
            super().perform_update(instance)
            sync_inventory_item(instance.item.location, instance.item.product)
            if instance._fully_dispensed is not None and instance._fully_dispensed:  # noqa
                instance.authorizing_request.dispense_status = (
                    MedicationRequestDispenseStatus.complete.value
                )
            else:
                instance.authorizing_request.dispense_status = (
                    MedicationRequestDispenseStatus.partial.value
                )
            if (
                current_obj.authorizing_request.dispense_status
                != instance.authorizing_request.dispense_status
            ):
                instance.authorizing_request.save()
            return instance

    def authorize_location_read(self, location):
        if not AuthorizationController.call(
            "can_list_location_medication_dispense", self.request.user, location
        ):
            raise PermissionDenied(
                "You do not have permission to read medication dispenses"
            )

    def authorize_encounter_read(self, encounter):
        if not AuthorizationController.call(
            "can_view_medication_dispense_for_encounter",
            self.request.user,
            encounter,
        ):
            raise PermissionDenied(
                "You do not have permission to read medication dispenses"
            )

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action in ["list", "summary"]:
            if "location" in self.request.GET:
                include_children = (
                    self.request.GET.get("include_children", "false").lower() == "true"
                )
                location = get_object_or_404(
                    FacilityLocation, external_id=self.request.GET.get("location")
                )
                self.authorize_location_read(location)
                if include_children:
                    queryset = queryset.filter(
                        Q(deliver_from=location)
                        | Q(deliver_from__parent_cache__overlap=[location.id])
                    )
                else:
                    queryset = queryset.filter(location=location)
            elif "encounter" in self.request.GET:
                encounter = get_object_or_404(
                    Encounter, external_id=self.request.GET.get("encounter")
                )
                self.authorize_encounter_read(encounter)
                queryset = queryset.filter(encounter=encounter)
            else:
                raise ValidationError("Location or encounter is required")
        return queryset

    @action(methods=["GET"], detail=False)
    def summary(self, request, *args, **kwargs):
        queryset = (
            self.filter_queryset(self.get_queryset())
            .values("encounter_id")
            .annotate(dcount=Count("encounter_id"))
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            encounters = Encounter.objects.filter(
                id__in=[x["encounter_id"] for x in page]
            )
            encounters = {
                x.id: EncounterListSpec.serialize(x).to_json() for x in encounters
            }
            data = [
                {
                    "encounter": encounters.get(x["encounter_id"], None),
                    "count": x["dcount"],
                }
                for x in page
            ]
            return paginator.get_paginated_response(data)
        return Response({})
