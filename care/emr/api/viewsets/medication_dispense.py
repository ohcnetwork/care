from django.db import transaction
from django.db.models import Count
from django_filters import rest_framework as filters
from rest_framework.decorators import action
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
from care.emr.models.medication_dispense import MedicationDispense
from care.emr.resources.charge_item.apply_charge_item_definition import (
    apply_charge_item_definition,
)
from care.emr.resources.encounter.spec import EncounterListSpec
from care.emr.resources.inventory.inventory_item.sync_inventory_item import (
    sync_inventory_item,
)
from care.emr.resources.medication.dispense.spec import (
    MedicationDispenseReadSpec,
    MedicationDispenseUpdateSpec,
    MedicationDispenseWriteSpec,
)
from care.emr.resources.medication.request.spec import MedicationRequestDispenseStatus
from care.utils.filters.multiselect import MultiSelectFilter


class MedicationDispenseFilters(filters.FilterSet):
    status = MultiSelectFilter(field_name="status")
    category = filters.CharFilter(lookup_expr="iexact")
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    patient = filters.UUIDFilter(field_name="patient__external_id")
    location = filters.UUIDFilter(field_name="location__external_id")
    item = filters.UUIDFilter(field_name="item__external_id")
    authorizing_prescription = filters.UUIDFilter(
        field_name="authorizing_prescription__external_id"
    )
    exclude_status = MultiSelectFilter(field_name="status", exclude=True)


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
    filter_backends = [filters.DjangoFilterBackend]

    def perform_create(self, instance):
        with transaction.atomic():
            if instance.item.product.charge_item_definition:
                charge_item = apply_charge_item_definition(
                    instance.item.product.charge_item_definition,
                    instance.encounter,
                    quantity=instance.quantity,
                )
                charge_item.save()
                instance.charge_item = charge_item
            super().perform_create(instance)
            sync_inventory_item(instance.item)
            if instance.authorizing_prescription:
                instance.authorizing_prescription.dispense_status = (
                    MedicationRequestDispenseStatus.partial.value
                )
                instance.authorizing_prescription.save()

    def perform_update(self, instance):
        with transaction.atomic():
            sync_inventory_item(instance.item)
            return super().perform_update(instance)

    @action(methods=["GET"], detail=False)
    def summary(self, request, *args, **kwargs):
        # TODO : Add AuthZ
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
