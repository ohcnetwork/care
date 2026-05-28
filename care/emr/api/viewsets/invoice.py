from datetime import timedelta

from django.conf import settings
from django.db import transaction
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
from care.emr.locks.billing import (
    AccountLock,
    InvoiceCreateLock,
    InvoiceLock,
)
from care.emr.models.account import Account
from care.emr.models.charge_item import ChargeItem
from care.emr.models.invoice import Invoice
from care.emr.models.payment_reconciliation import PaymentReconciliation
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
from care.utils.filters.dummy_filter import DummyBooleanFilter
from care.utils.lock import ObjectLocked
from care.utils.shortcuts import get_object_or_404
from care.utils.time_util import care_now


class InvoiceFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    title = filters.CharFilter(lookup_expr="icontains")
    account = filters.UUIDFilter(field_name="account__external_id")
    patient = filters.UUIDFilter(field_name="patient__external_id")
    number = filters.CharFilter(lookup_expr="icontains")
    locked = filters.BooleanFilter()
    is_refund = filters.BooleanFilter()
    payment_reconciliation_present = DummyBooleanFilter()
    created_by = filters.UUIDFilter(field_name="created_by__external_id")


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

    def authorize_retrieve(self, instance):
        if instance.locked:
            self.check_invoice_lock_permission(instance)

    def get_queryset(self):
        queryset = super().get_queryset().select_related("account")
        facility = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_read_invoice_in_facility", self.request.user, facility
        ):
            raise PermissionDenied("Cannot read invoice")

        if self.request.GET.get("payment_reconciliation_present") is not None:
            payment_reconciliation_present = (
                str(self.request.GET.get("payment_reconciliation_present")).lower()
                == "true"
            )
            account_id = self.request.GET.get("account")
            if payment_reconciliation_present and not account_id:
                raise ValidationError(
                    "Account is required when payment reconciliation filter is present"
                )
            if payment_reconciliation_present:
                queryset = queryset.filter(
                    id__in=PaymentReconciliation.objects.filter(
                        account__external_id=account_id
                    ).values("target_invoice_id")
                )
            else:
                queryset = queryset.exclude(
                    id__in=PaymentReconciliation.objects.filter(
                        account__external_id=account_id
                    ).values("target_invoice_id")
                )

        return queryset.filter(facility=facility)

    def perform_create(self, instance):
        instance.status = InvoiceStatusOptions.draft.value
        instance.facility = self.get_facility_obj()
        with transaction.atomic(), AccountLock(instance.account):
            charge_items = ChargeItem.objects.filter(
                account=instance.account,
                status=ChargeItemStatusOptions.billable.value,
                external_id__in=instance.charge_items,
            )
            instance.charge_items = list(charge_items.values_list("id", flat=True))
            try:
                with InvoiceCreateLock():
                    if not instance.number:
                        instance.number = (
                            evaluate_invoice_identifier_default_expression(
                                instance.facility
                            )
                        )
                    super().perform_create(instance)
            except ObjectLocked as e:
                raise ValidationError("Invoice creation failed") from e
            charge_items.update(
                status=ChargeItemStatusOptions.billed.value, paid_invoice=instance
            )
            sync_invoice_items(instance)
            instance.save()
        rebalance_account_task(instance.account.id)

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

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_write_invoice_in_facility", self.request.user, model_instance.facility
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
                if (
                    instance.status == InvoiceStatusOptions.issued.value
                    and len(instance.charge_items) == 0
                ):
                    raise ValidationError("Invoice must have at least one charge item")
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
                        status=ChargeItemStatusOptions.paid.value,
                        paid_invoice=instance,
                        paid_on=care_now(),
                    )
            super().perform_update(instance)
            rebalance_account_task(instance.account.id)
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
        with AccountLock(invoice.account):
            self.authorize_update({}, invoice)
            self.check_invoice_in_draft(invoice)
            request_params = AttachChargeItemToInvoiceRequest(**request.data)
            with transaction.atomic():
                charge_items = ChargeItem.objects.filter(
                    external_id__in=request_params.charge_items,
                    account=invoice.account,
                    status=ChargeItemStatusOptions.billable.value,
                )
                extra_charge_items = list(charge_items.values_list("id", flat=True))
                invoice.charge_items = invoice.charge_items + extra_charge_items
                sync_invoice_items(invoice)
                invoice.updated_by = self.request.user
                invoice.save()
                charge_items.update(
                    status=ChargeItemStatusOptions.billed.value,
                    paid_invoice=invoice,
                )
        rebalance_account_task(invoice.account.id)
        return Response(InvoiceRetrieveSpec.serialize(invoice).to_json())

    @extend_schema(
        request=RemoveChargeItemFromInvoiceRequest,
    )
    @action(methods=["POST"], detail=True)
    def remove_item_from_invoice(self, request, *args, **kwargs):
        invoice = self.get_object()
        with AccountLock(invoice.account):
            self.authorize_update({}, invoice)
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
                    invoice.updated_by = self.request.user
                    invoice.save()
                    charge_item.status = ChargeItemStatusOptions.billable.value
                    charge_item.paid_invoice = None
                    charge_item.paid_on = None
                    charge_item.save()
            except ValueError as e:
                raise ValidationError("Charge item not found in invoice") from e
        rebalance_account_task(invoice.account.id)
        return Response(InvoiceRetrieveSpec.serialize(invoice).to_json())

    @action(methods=["POST"], detail=True)
    def attach_account_to_invoice(self, request, *args, **kwargs):
        invoice = self.get_object()
        with AccountLock(invoice.account):
            self.authorize_update({}, invoice)
            self.check_invoice_in_draft(invoice)
            with transaction.atomic():
                charge_items = ChargeItem.objects.filter(
                    account=invoice.account,
                    status=ChargeItemStatusOptions.billable.value,
                )
                invoice.charge_items = charge_items.values_list("id", flat=True)
                sync_invoice_items(invoice)
                invoice.updated_by = self.request.user
                invoice.save()
                charge_items.update(
                    status=ChargeItemStatusOptions.billed.value, paid_invoice=invoice
                )
        rebalance_account_task(invoice.account.id)
        return Response(InvoiceRetrieveSpec.serialize(invoice).to_json())

    @action(methods=["POST"], detail=True)
    def cancel_invoice(self, request, *args, **kwargs):
        invoice = self.get_object()
        with AccountLock(invoice.account):
            if invoice.created_date >= care_now() - timedelta(
                minutes=settings.INVOICE_FREE_CANCEL_PERIOD_MINUTES
            ):
                if not AuthorizationController.call(
                    "can_write_invoice_in_facility", self.request.user, invoice.facility
                ):
                    raise PermissionDenied("Cannot cancel invoice")
            elif not AuthorizationController.call(
                "can_destroy_invoice_in_facility", self.request.user, invoice.facility
            ):
                raise PermissionDenied("Cannot cancel invoice")
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
                    status=ChargeItemStatusOptions.billable.value,
                    paid_invoice=None,
                    paid_on=None,
                )
                invoice.updated_by = self.request.user
                invoice.save()
        return Response(InvoiceRetrieveSpec.serialize(invoice).to_json())

    def check_invoice_lock_permission(self, invoice):
        if not AuthorizationController.call(
            "can_manage_locked_invoice_in_facility", self.request.user, invoice.facility
        ):
            raise PermissionDenied("Locked invoice permission denied.")

    @action(methods=["POST"], detail=True)
    def lock(self, request, *args, **kwargs):
        invoice = self.get_object()
        self.check_invoice_lock_permission(invoice)
        if invoice.locked:
            raise ValidationError("Invoice is already locked")
        invoice.locked = True
        invoice.lock_history.append(
            {
                "user": self.request.user.id,
                "timestamp": str(care_now()),
                "action": "lock",
            }
        )
        invoice.updated_by = self.request.user
        invoice.save()
        return Response(InvoiceRetrieveSpec.serialize(invoice).to_json())

    @action(methods=["POST"], detail=True)
    def unlock(self, request, *args, **kwargs):
        invoice = self.get_object()
        self.check_invoice_lock_permission(invoice)
        if not invoice.locked:
            raise ValidationError("Invoice is not locked")
        invoice.locked = False
        invoice.lock_history.append(
            {
                "user": self.request.user.id,
                "timestamp": str(care_now()),
                "action": "unlock",
            }
        )
        invoice.updated_by = self.request.user
        invoice.save()
        return Response(InvoiceRetrieveSpec.serialize(invoice).to_json())
