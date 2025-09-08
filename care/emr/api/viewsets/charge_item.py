from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel, model_validator
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRTagMixin,
    EMRUpdateMixin,
    EMRUpsertMixin,
)
from care.emr.models.account import Account
from care.emr.models.charge_item import ChargeItem
from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.encounter import Encounter
from care.emr.models.location import FacilityLocationEncounter
from care.emr.models.patient import Patient
from care.emr.models.service_request import ServiceRequest
from care.emr.registries.system_questionnaire.system_questionnaire import (
    InternalQuestionnaireRegistry,
)
from care.emr.resources.account.default_account import get_default_account
from care.emr.resources.charge_item.apply_charge_item_definition import (
    apply_charge_item_definition,
)
from care.emr.resources.charge_item.handle_charge_item_cancel import (
    handle_charge_item_cancel,
)
from care.emr.resources.charge_item.spec import (
    CHARGE_ITEM_CANCELLED_STATUS,
    ChargeItemReadSpec,
    ChargeItemResourceOptions,
    ChargeItemSpec,
    ChargeItemWriteSpec,
)
from care.emr.resources.charge_item.sync_charge_item_costs import sync_charge_item_costs
from care.emr.resources.encounter.constants import COMPLETED_CHOICES
from care.emr.resources.invoice.spec import InvoiceStatusOptions
from care.emr.resources.invoice.sync_items import sync_invoice_items
from care.emr.resources.questionnaire.spec import SubjectType
from care.emr.resources.service_request.spec import SERVICE_REQUEST_COMPLETED_CHOICES
from care.emr.resources.tag.config_spec import TagResource
from care.emr.tagging.filters import SingleFacilityTagFilter
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController


class ChargeItemDefinitionFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    title = filters.CharFilter(lookup_expr="icontains")
    account = filters.UUIDFilter(field_name="account__external_id")
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    service_resource = filters.CharFilter(lookup_expr="iexact")
    service_resource_id = filters.CharFilter(lookup_expr="iexact")


class ApplyChargeItemDefinitionRequest(BaseModel):
    charge_item_definition: str
    quantity: int
    encounter: UUID4 | None = None
    patient: UUID4 | None = None

    service_resource: ChargeItemResourceOptions | None = None
    service_resource_id: str | None = None

    @model_validator(mode="after")
    def validate_encounter_patient(self):
        if not self.encounter and not self.patient:
            raise ValueError("Encounter or patient is required")
        return self

    @model_validator(mode="after")
    def validate_service_resource(self):
        if self.service_resource and not self.service_resource_id:
            raise ValueError("Service resource id is required.")
        return self


class ApplyMultipleChargeItemDefinitionRequest(BaseModel):
    requests: list[ApplyChargeItemDefinitionRequest]


def validate_service_resource(
    facility, service_resource, service_resource_id, patient, encounter=None
):
    # TODO Validate with Patient and Encounter
    try:
        if service_resource == ChargeItemResourceOptions.service_request.value:
            qs = ServiceRequest.objects.filter(
                facility=facility, external_id=service_resource_id, patient=patient
            )
            if encounter:
                qs = qs.filter(encounter=encounter)
            return qs.exclude(status__in=SERVICE_REQUEST_COMPLETED_CHOICES).exists()
        if service_resource == ChargeItemResourceOptions.bed_association.value:
            if not encounter:
                raise ValidationError("Encounter is required")
            if encounter.facility != facility:
                raise ValidationError("Encounter is not associated with the facility")
            if encounter.status in COMPLETED_CHOICES:
                raise ValidationError("Encounter is already completed")
            qs = FacilityLocationEncounter.objects.filter(
                encounter=encounter,
                external_id=service_resource_id,
            )
            return qs.exists()
        raise ValidationError("Invalid service resource")
    except Exception:
        return False


class ChargeItemViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRUpsertMixin,
    EMRListMixin,
    EMRTagMixin,
    EMRBaseViewSet,
):
    database_model = ChargeItem
    pydantic_model = ChargeItemWriteSpec
    pydantic_update_model = ChargeItemSpec
    pydantic_read_model = ChargeItemReadSpec
    filterset_class = ChargeItemDefinitionFilters
    filter_backends = [
        filters.DjangoFilterBackend,
        OrderingFilter,
        SingleFacilityTagFilter,
    ]
    ordering_fields = ["created_date", "modified_date"]
    questionnaire_type = "charge_item"
    questionnaire_title = "Charge Item"
    questionnaire_description = "Charge Item"
    questionnaire_subject_type = SubjectType.encounter.value
    resource_type = TagResource.charge_item

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def get_serializer_create_context(self):
        return {"facility": self.get_facility_obj()}

    def perform_create(self, instance):
        instance.facility = self.get_facility_obj()
        if instance.service_resource and not validate_service_resource(
            instance.facility,
            instance.service_resource,
            instance.service_resource_id,
            instance.patient,
            instance.encounter,
        ):
            raise ValidationError("Invalid service resource")
        if not instance.account_id:
            instance.account = get_default_account(instance.patient, instance.facility)
        sync_charge_item_costs(instance)
        super().perform_create(instance)

    def validate_data(self, instance, model_obj=None):
        if (
            model_obj
            and model_obj.paid_invoice
            and model_obj.paid_invoice.status
            in [
                InvoiceStatusOptions.balanced.value,
                InvoiceStatusOptions.issued.value,
            ]
        ):
            raise ValidationError(
                "Invoice is already balanced or issued, Cancel Invoice before updating charge item"
            )
        if model_obj and model_obj.status in CHARGE_ITEM_CANCELLED_STATUS:
            raise ValidationError("No updates allowed on cancelled charge item")

        return super().validate_data(instance, model_obj)

    def perform_update(self, instance):
        with transaction.atomic():
            # TODO Lock Charge item and Invoice
            old_obj = ChargeItem.objects.get(id=instance.id)
            if (
                old_obj.status != instance.status
                and instance.status in CHARGE_ITEM_CANCELLED_STATUS
            ):
                handle_charge_item_cancel(instance)
            sync_charge_item_costs(instance)
            super().perform_update(instance)
            if (
                instance.paid_invoice
                and instance.paid_invoice.status == InvoiceStatusOptions.draft.value
                and instance.status not in CHARGE_ITEM_CANCELLED_STATUS
            ):
                sync_invoice_items(instance.paid_invoice)
                instance.paid_invoice.save()

    def authorize_create(self, instance):
        facility = self.get_facility_obj()
        if instance.encounter:
            encounter = get_object_or_404(Encounter, external_id=instance.encounter)
            if encounter.facility != facility:
                raise ValidationError("Encounter is not associated with the facility")
        if instance.account:
            account = get_object_or_404(Account, external_id=instance.account)
            if account.facility != facility:
                raise ValidationError("Account is not associated with the facility")
        if not AuthorizationController.call(
            "can_create_charge_item_in_facility",
            self.request.user,
            facility,
        ):
            raise PermissionDenied("Access Denied to Charge Item")
        return super().authorize_create(instance)

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_update_charge_item_in_facility",
            self.request.user,
            model_instance.facility,
        ):
            raise PermissionDenied("Access Denied to Charge Item")

    def get_queryset(self):
        facility = self.get_facility_obj()
        queryset = super().get_queryset().filter(facility=facility)
        if not AuthorizationController.call(
            "can_read_charge_item_in_facility",
            self.request.user,
            facility,
        ):
            raise PermissionDenied("Access Denied to Charge Item")

        return queryset.select_related("paid_invoice", "charge_item_definition")

    @extend_schema(
        request=ApplyMultipleChargeItemDefinitionRequest,
    )
    @action(methods=["POST"], detail=False)
    def apply_charge_item_defs(self, request, *args, **kwargs):
        facility = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_create_charge_item_in_facility",
            self.request.user,
            facility,
        ):
            raise PermissionDenied("Access Denied to Charge Item")
        request_params = ApplyMultipleChargeItemDefinitionRequest(**request.data)
        with transaction.atomic():
            for charge_item_request in request_params.requests:
                charge_item_definition = get_object_or_404(
                    ChargeItemDefinition,
                    slug=charge_item_request.charge_item_definition,
                )
                if (
                    charge_item_definition.facility
                    and charge_item_definition.facility != facility
                ):
                    raise ValidationError(
                        "Charge item definition is not associated with the facility"
                    )
                patient = None
                if charge_item_request.patient:
                    patient = get_object_or_404(
                        Patient,
                        external_id=charge_item_request.patient,
                    )
                encounter = None
                if charge_item_request.encounter:
                    encounter = get_object_or_404(
                        Encounter,
                        external_id=charge_item_request.encounter,
                        facility=facility,
                    )

                if (
                    charge_item_request.service_resource
                    and not validate_service_resource(
                        facility,
                        charge_item_request.service_resource,
                        charge_item_request.service_resource_id,
                        patient,
                        encounter,
                    )
                ):
                    raise ValidationError("Invalid service resource")
                if not encounter:
                    if charge_item_request.patient:
                        patient = get_object_or_404(
                            Patient,
                            external_id=charge_item_request.patient,
                        )
                    else:
                        raise ValidationError("Patient is required")
                else:
                    patient = encounter.patient
                encounter = None
                quantity = charge_item_request.quantity
                charge_item = apply_charge_item_definition(
                    charge_item_definition,
                    patient,
                    facility,
                    encounter=encounter,
                    quantity=quantity,
                )
                if charge_item_request.service_resource:
                    charge_item.service_resource = charge_item_request.service_resource
                    charge_item.service_resource_id = (
                        charge_item_request.service_resource_id
                    )
                charge_item.save()
        return Response({})


InternalQuestionnaireRegistry.register(ChargeItemViewSet)
