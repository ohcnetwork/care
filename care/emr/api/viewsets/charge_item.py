from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel, Field, model_validator
from rest_framework import status
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
from care.emr.models.organization import FacilityOrganizationUser
from care.emr.models.patient import Patient
from care.emr.models.service_request import ServiceRequest
from care.emr.registries.system_questionnaire.system_questionnaire import (
    InternalQuestionnaireRegistry,
)
from care.emr.resources.account.default_account import get_default_account
from care.emr.resources.account.spec import AccountStatusOptions
from care.emr.resources.account.sync_items import rebalance_account_task
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
    ChargeItemStatusOptions,
    ChargeItemUpdateSpec,
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
from care.users.models import User
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.shortcuts import get_object_or_404
from care.utils.time_util import care_now


class ChargeItemFilters(filters.FilterSet):
    status = MultiSelectFilter(field_name="status")
    title = filters.CharFilter(lookup_expr="icontains")
    account = filters.UUIDFilter(field_name="account__external_id")
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    service_resource = MultiSelectFilter()
    service_resource_id = filters.CharFilter(lookup_expr="iexact")
    patient = filters.UUIDFilter(field_name="patient__external_id")
    paid_on = filters.DateTimeFromToRangeFilter(field_name="paid_on")
    performer_actor = filters.UUIDFilter(field_name="performer_actor__external_id")
    created_date = filters.DateTimeFromToRangeFilter(field_name="created_date")
    created_by = filters.UUIDFilter(field_name="created_by__external_id")


class ApplyChargeItemDefinitionRequest(BaseModel):
    charge_item_definition: str
    quantity: int
    encounter: UUID4 | None = None
    patient: UUID4 | None = None
    performer_actor: UUID4 | None = None
    account: UUID4 | None = None

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


class ChargeItemAccountChangeRequest(BaseModel):
    charge_items: list[UUID4] = Field(min_length=1, max_length=100)
    target_account: UUID4


class ApplyMultipleChargeItemDefinitionRequest(BaseModel):
    requests: list[ApplyChargeItemDefinitionRequest]


def validate_service_resource(
    facility, service_resource, service_resource_id, patient, encounter=None
):
    try:
        if service_resource == ChargeItemResourceOptions.service_request.value:
            qs = ServiceRequest.objects.filter(
                facility=facility, external_id=service_resource_id
            )
            if encounter:
                qs = qs.filter(encounter=encounter)
            else:
                qs = qs.filter(patient=patient)
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
    pydantic_update_model = ChargeItemUpdateSpec
    pydantic_read_model = ChargeItemReadSpec
    filterset_class = ChargeItemFilters
    filter_backends = [
        filters.DjangoFilterBackend,
        OrderingFilter,
        SingleFacilityTagFilter,
    ]
    ordering_fields = ["created_date", "modified_date", "title"]
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
        if (
            instance.performer_actor
            and not FacilityOrganizationUser.objects.filter(
                user_id=instance.performer_actor.id,
                organization__facility=instance.facility,
            ).exists()
        ):
            raise ValidationError("Performer is not associated with the facility")
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
        last_obj = None
        if model_obj:
            last_obj = ChargeItem.objects.get(id=model_obj.id)
        if (
            model_obj
            and last_obj
            and last_obj.status != instance.status
            and instance.status
            in [
                ChargeItemStatusOptions.billed.value,
                ChargeItemStatusOptions.paid.value,
            ]
        ):
            raise ValidationError("Charge item status cannot be manually changed.")
        return super().validate_data(instance, model_obj)

    def authorize_cancel(self, instance):
        if instance.created_date >= care_now() - timedelta(
            minutes=settings.CHARGE_ITEM_FREE_CANCEL_PERIOD_MINUTES
        ):
            return True
        if not AuthorizationController.call(
            "can_cancel_charge_item_in_facility",
            self.request.user,
            instance.facility,
        ):
            raise PermissionDenied("Access Denied to Cancel Charge Item")
        # Write permission is already checked
        return True

    def perform_update(self, instance):
        with transaction.atomic():
            # TODO Lock Charge item and Invoice
            old_obj = ChargeItem.objects.get(id=instance.id)
            sync = True
            if (
                instance.charge_item_definition
                and not instance.charge_item_definition.can_edit_charge_item
            ):
                instance.unit_price_components = old_obj.unit_price_components
                instance.total_price_components = old_obj.total_price_components
                instance.total_price = old_obj.total_price
                instance.quantity = old_obj.quantity
                sync = False
            if (
                old_obj.status != instance.status
                and instance.status in CHARGE_ITEM_CANCELLED_STATUS
            ):
                self.authorize_cancel(instance)
                handle_charge_item_cancel(instance)
                sync = False
            if sync:
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
        return True

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
        negative_allowed = AuthorizationController.call(
            "can_create_negative_charge_item_in_facility",
            self.request.user,
            facility,
        )
        request_params = ApplyMultipleChargeItemDefinitionRequest(**request.data)
        with transaction.atomic():
            for charge_item_request in request_params.requests:
                charge_item_definition = get_object_or_404(
                    ChargeItemDefinition,
                    slug=charge_item_request.charge_item_definition,
                    facility=facility,
                )
                if (
                    charge_item_definition.facility
                    and charge_item_definition.facility != facility
                ):
                    raise ValidationError(
                        "Charge item definition is not associated with the facility"
                    )
                patient = None
                encounter = None
                if charge_item_request.encounter:
                    encounter = get_object_or_404(
                        Encounter,
                        external_id=charge_item_request.encounter,
                        facility=facility,
                    )
                    patient = encounter.patient
                elif charge_item_request.patient:
                    patient = get_object_or_404(
                        Patient,
                        external_id=charge_item_request.patient,
                    )
                else:
                    raise ValidationError("Patient or encounter is required")
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
                kwargs = {}
                if charge_item_request.account:
                    kwargs["account"] = get_object_or_404(
                        Account,
                        external_id=charge_item_request.account,
                        facility=facility,
                        patient=patient,
                        status=AccountStatusOptions.active.value,
                    )
                quantity = charge_item_request.quantity
                charge_item = apply_charge_item_definition(
                    charge_item_definition,
                    patient,
                    facility,
                    encounter=encounter,
                    quantity=quantity,
                    negative_allowed=negative_allowed,
                    **kwargs,
                )
                if charge_item_request.service_resource:
                    charge_item.service_resource = charge_item_request.service_resource
                    charge_item.service_resource_id = (
                        charge_item_request.service_resource_id
                    )
                if charge_item_request.performer_actor:
                    charge_item.performer_actor = get_object_or_404(
                        User.objects.only("id"),
                        external_id=charge_item_request.performer_actor,
                    )
                    if not FacilityOrganizationUser.objects.filter(
                        user_id=charge_item.performer_actor.id,
                        organization__facility=facility,
                    ).exists():
                        raise ValidationError(
                            "Performer is not associated with the facility"
                        )

                charge_item.created_by = request.user
                charge_item.updated_by = request.user
                charge_item.save()
        return Response({})

    @extend_schema(
        request=ChargeItemAccountChangeRequest,
    )
    @action(methods=["POST"], detail=False)
    def change_account(self, request, *args, **kwargs):
        """
        Change accounts related to a charge item.
        """
        facility = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_create_charge_item_in_facility",
            self.request.user,
            facility,
        ):
            raise PermissionDenied("Access Denied to Charge Item")
        request_params = ChargeItemAccountChangeRequest(**request.data)
        target_account = get_object_or_404(
            Account, external_id=request_params.target_account, facility=facility
        )
        source_accounts = [target_account.id]  # For Rebalancing all related accounts
        with transaction.atomic():
            for charge_item_request in request_params.charge_items:
                charge_item = get_object_or_404(
                    ChargeItem,
                    external_id=charge_item_request,
                    facility=facility,
                    patient=target_account.patient,
                )
                if charge_item.status != ChargeItemStatusOptions.billable.value:
                    raise ValidationError({"charge_item": "should be billable"})
                source_accounts.append(charge_item.account_id)
                charge_item.account = target_account
                charge_item.updated_by = request.user
                charge_item.save(update_fields=["account", "updated_by"])

        for account_id in list(set(source_accounts)):
            rebalance_account_task(account_id)
        return Response({}, status=status.HTTP_201_CREATED)


InternalQuestionnaireRegistry.register(ChargeItemViewSet)
