from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
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
)
from care.emr.locks.billing import InvoiceLock
from care.emr.models.account import Account
from care.emr.models.charge_item import ChargeItem
from care.emr.models.invoice import Invoice
from care.emr.resources.account.sync_items import rebalance_account_task
from care.emr.resources.charge_item.spec import ChargeItemStatusOptions
from care.emr.resources.invoice.default_expression_evaluator import (
    evaluate_invoice_identifier_default_expression,
)
from care.emr.resources.invoice.spec import (
    INVOICE_CANCELLED_STATUS,
    BaseInvoiceSpec,
    InvoiceReadSpec,
    InvoiceRetrieveSpec,
    InvoiceStatusOptions,
    InvoiceWriteSpec,
)
from care.emr.resources.invoice.sync_items import sync_invoice_items
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController


class InvoiceFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    title = filters.CharFilter(lookup_expr="icontains")
    account = filters.UUIDFilter(field_name="account__external_id")
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    number = filters.CharFilter(lookup_expr="icontains")


class AttachChargeItemToInvoiceRequest(BaseModel):
    charge_items: list[UUID4]


class RemoveChargeItemFromInvoiceRequest(BaseModel):
    charge_item: UUID4


class InvoiceCancelReasonRequest(BaseModel):
    reason: str


class InvoiceViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
):
    database_model = Invoice
    pydantic_model = InvoiceWriteSpec
    pydantic_update_model = BaseInvoiceSpec
    pydantic_read_model = InvoiceReadSpec
    pydantic_retrieve_model = InvoiceRetrieveSpec
    filterset_class = InvoiceFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        facility = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_read_invoice_in_facility", self.request.user, facility
        ):
            raise PermissionDenied("Cannot read invoice")
        return queryset.filter(facility=facility)

    def perform_create(self, instance):
        instance.status = InvoiceStatusOptions.draft.value
        instance.facility = self.get_facility_obj()
        with transaction.atomic():
            charge_items = ChargeItem.objects.filter(
                account=instance.account,
                status=ChargeItemStatusOptions.billable.value,
                external_id__in=instance.charge_items,
            )
            instance.charge_items = list(charge_items.values_list("id", flat=True))
            # TODO : Lock only one at a time
            if not instance.number:
                instance.number = evaluate_invoice_identifier_default_expression(
                    instance.facility
                )
            super().perform_create(instance)
            charge_items.update(
                status=ChargeItemStatusOptions.billed.value, paid_invoice=instance
            )
            sync_invoice_items(instance)
            instance.save()
            rebalance_account_task.delay(instance.account.id)

        return instance

    def authorize_create(self, instance):
        facility = self.get_facility_obj()
        account = get_object_or_404(Account, external_id=instance.account)
        if account.facility != facility:
            raise ValidationError("Account is not associated with the facility")
        if not AuthorizationController.call(
            "can_write_invoice_in_facility", self.request.user, facility
        ):
            raise PermissionDenied("Cannot write invoice")

    def perform_update(self, instance):
        with InvoiceLock(instance):
            old_invoice = Invoice.objects.get(id=instance.id)
            if old_invoice.status != instance.status:
                if instance.status in INVOICE_CANCELLED_STATUS:
                    raise ValidationError(
                        "Call the cancel invoice API to cancel the invoice"
                    )
                if (
                    old_invoice.status in INVOICE_CANCELLED_STATUS
                    and instance.status not in INVOICE_CANCELLED_STATUS
                ):
                    raise ValidationError("Invoice is already cancelled")
                if old_invoice.status == InvoiceStatusOptions.balanced.value:
                    raise ValidationError("Invoice is already balanced")
                if (
                    old_invoice.status == InvoiceStatusOptions.issued.value
                    and instance.status == InvoiceStatusOptions.draft.value
                ):
                    raise ValidationError("Invoice is already issued")
                if (
                    old_invoice.status == InvoiceStatusOptions.draft.value
                    and instance.status == InvoiceStatusOptions.balanced.value
                ):
                    raise ValidationError("Invoice needs to be issued before balancing")
                if (
                    old_invoice.status == InvoiceStatusOptions.issued.value
                    and instance.status == InvoiceStatusOptions.balanced.value
                ):
                    ChargeItem.objects.filter(
                        account=instance.account,
                        status=ChargeItemStatusOptions.billed.value,
                        id__in=instance.charge_items,
                    ).update(
                        status=ChargeItemStatusOptions.paid.value, paid_invoice=instance
                    )
            super().perform_update(instance)
            rebalance_account_task.delay(instance.account.id)
        return instance

    def check_invoice_in_draft(self, instance):
        if instance.status == InvoiceStatusOptions.draft.value:
            return True
        raise ValidationError("Invoice is not in draft")

    @extend_schema(
        request=AttachChargeItemToInvoiceRequest,
    )
    @action(methods=["POST"], detail=True)
    def attach_items_to_invoice(self, request, *args, **kwargs):
        invoice = self.get_object()
        with InvoiceLock(invoice):
            self.authorize_create(invoice)
            self.check_invoice_in_draft(invoice)
            request_params = AttachChargeItemToInvoiceRequest(**request.data)
            with transaction.atomic():
                charge_items = ChargeItem.objects.filter(
                    external_id__in=request_params.charge_items,
                    account=invoice.account,
                    status=ChargeItemStatusOptions.billable.value,
                )
                invoice.charge_items = invoice.charge_items + list(
                    charge_items.values_list("id", flat=True)
                )
                sync_invoice_items(invoice)
                invoice.save()
                charge_items.update(
                    status=ChargeItemStatusOptions.billed.value, paid_invoice=invoice
                )
        return Response(InvoiceRetrieveSpec.serialize(invoice).to_json())

    @extend_schema(
        request=RemoveChargeItemFromInvoiceRequest,
    )
    @action(methods=["POST"], detail=True)
    def remove_item_from_invoice(self, request, *args, **kwargs):
        invoice = self.get_object()
        with InvoiceLock(invoice):
            self.authorize_create(invoice)
            self.check_invoice_in_draft(invoice)
            request_params = RemoveChargeItemFromInvoiceRequest(**request.data)
            charge_item = get_object_or_404(
                ChargeItem,
                external_id=request_params.charge_item,
                account=invoice.account,
            )
            try:
                with transaction.atomic():
                    invoice.charge_items.remove(charge_item.id)
                    sync_invoice_items(invoice)
                    invoice.save()
                    charge_item.status = ChargeItemStatusOptions.billable.value
                    charge_item.paid_invoice = None
                    charge_item.save()
            except ValueError as e:
                raise ValidationError("Charge item not found in invoice") from e

        return Response(InvoiceRetrieveSpec.serialize(invoice).to_json())

    @action(methods=["POST"], detail=True)
    def attach_account_to_invoice(self, request, *args, **kwargs):
        invoice = self.get_object()
        with InvoiceLock(invoice):
            self.authorize_create(invoice)
            self.check_invoice_in_draft(invoice)
            with transaction.atomic():
                charge_items = ChargeItem.objects.filter(
                    account=invoice.account,
                    status=ChargeItemStatusOptions.billable.value,
                )
                invoice.charge_items = charge_items.values_list("id", flat=True)
                sync_invoice_items(invoice)
                invoice.save()
                charge_items.update(
                    status=ChargeItemStatusOptions.billed.value, paid_invoice=invoice
                )
        return Response(InvoiceRetrieveSpec.serialize(invoice).to_json())

    @action(methods=["POST"], detail=True)
    def cancel_invoice(self, request, *args, **kwargs):
        invoice = self.get_object()
        with InvoiceLock(invoice):
            if not AuthorizationController.call(
                "can_destroy_invoice_in_facility", self.request.user, invoice.facility
            ):
                raise PermissionDenied("Cannot write invoice")
            if invoice.status in INVOICE_CANCELLED_STATUS:
                raise ValidationError("Invoice is already cancelled")
            request_params = InvoiceCancelReasonRequest(**request.data)
            if request_params.reason not in INVOICE_CANCELLED_STATUS:
                raise ValidationError("Invalid reason")
            with transaction.atomic():
                invoice.status = request_params.reason
                ChargeItem.objects.filter(
                    account=invoice.account,
                    id__in=invoice.charge_items,
                ).update(
                    status=ChargeItemStatusOptions.billable.value, paid_invoice=None
                )
                invoice.save()
        return Response(InvoiceRetrieveSpec.serialize(invoice).to_json())
