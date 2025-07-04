from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter

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
from care.emr.resources.payment_reconciliation.spec import (
    BasePaymentReconciliationSpec,
    PaymentReconciliationReadSpec,
    PaymentReconciliationWriteSpec,
)
from care.facility.models.facility import Facility


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

    def perform_create(self, instance):
        instance.facility = self.get_facility_obj()
        super().perform_create(instance)

    def authorize_create(self, instance):
        facility = self.get_facility_obj()
        account = get_object_or_404(Account, external_id=instance.account)
        if account.facility != facility:
            raise ValidationError("Account is not associated with the facility")
        if instance.target_invoice:
            invoice = get_object_or_404(
                Invoice, external_id=instance.target_invoice, account=account
            )
            if invoice.facility != facility:
                raise ValidationError("Invoice is not associated with the facility")
            # TODO: AuthZ pending
        return super().authorize_create(instance)
