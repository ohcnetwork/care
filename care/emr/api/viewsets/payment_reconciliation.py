from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from pydantic import BaseModel
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
from care.emr.models.account import Account
from care.emr.models.invoice import Invoice
from care.emr.models.payment_reconciliation import PaymentReconciliation
from care.emr.resources.account.sync_items import rebalance_account_task
from care.emr.resources.payment_reconciliation.spec import (
    BasePaymentReconciliationSpec,
    PaymentReconciliationReadSpec,
    PaymentReconciliationStatusOptions,
    PaymentReconciliationWriteSpec,
)
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController


class PaymentReconciliationCancelRequest(BaseModel):
    reason: PaymentReconciliationStatusOptions


class PaymentReconciliationFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    target_invoice = filters.UUIDFilter(field_name="target_invoice__external_id")
    reconciliation_type = filters.CharFilter(lookup_expr="iexact")
    account = filters.UUIDFilter(field_name="account__external_id")


class PaymentReconciliationViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
):
    database_model = PaymentReconciliation
    pydantic_model = PaymentReconciliationWriteSpec
    pydantic_update_model = BasePaymentReconciliationSpec
    pydantic_read_model = PaymentReconciliationReadSpec
    filterset_class = PaymentReconciliationFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date", "payment_datetime"]

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        facility = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_read_payment_reconciliation_in_facility",
            self.request.user,
            facility,
        ):
            raise PermissionDenied("Cannot read payment reconciliation")
        return queryset.filter(facility=facility)

    def perform_create(self, instance):
        instance.facility = self.get_facility_obj()
        super().perform_create(instance)
        rebalance_account_task.delay(instance.account.id)

    def perform_update(self, instance):
        old_instance = self.get_object()
        if old_instance.status != instance.status and instance.status in [
            PaymentReconciliationStatusOptions.cancelled.value,
            PaymentReconciliationStatusOptions.entered_in_error.value,
        ]:
            raise ValidationError(
                "Cannot update payment reconciliation, use the cancel endpoint instead"
            )
        super().perform_update(instance)
        rebalance_account_task.delay(instance.account.id)

    def authorize_create(self, instance):
        facility = self.get_facility_obj()
        account = get_object_or_404(Account, external_id=instance.account)
        if not AuthorizationController.call(
            "can_write_payment_reconciliation_in_facility",
            self.request.user,
            facility,
        ):
            raise PermissionDenied("Cannot write payment reconciliation")
        if account.facility != facility:
            raise ValidationError("Account is not associated with the facility")
        if instance.target_invoice:
            invoice = get_object_or_404(
                Invoice, external_id=instance.target_invoice, account=account
            )
            if invoice.facility != facility:
                raise ValidationError("Invoice is not associated with the facility")

    @action(methods=["POST"], detail=True)
    def cancel_payment_reconciliation(self, request, *args, **kwargs):
        request_data = PaymentReconciliationCancelRequest(**request.data)
        if request_data.reason not in [
            PaymentReconciliationStatusOptions.cancelled.value,
            PaymentReconciliationStatusOptions.entered_in_error.value,
        ]:
            raise ValidationError("Invalid reason")
        instance = self.get_object()
        if not AuthorizationController.call(
            "can_destroy_payment_reconciliation_in_facility",
            self.request.user,
            instance.facility,
        ):
            raise PermissionDenied("Cannot write payment reconciliation")
        instance.status = request_data.reason
        instance.save()
        rebalance_account_task.delay(instance.account.id)
        return Response(PaymentReconciliationReadSpec.serialize(instance).to_json())
