from datetime import timedelta

from django.conf import settings
from django.http import Http404
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel, Field
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
    EMRUpdateMixin,
)
from care.emr.locks.billing import AccountLock
from care.emr.models.account import Account
from care.emr.models.invoice import Invoice
from care.emr.models.location import FacilityLocation
from care.emr.models.payment_reconciliation import PaymentReconciliation
from care.emr.resources.account.sync_items import rebalance_account_task
from care.emr.resources.payment_reconciliation.spec import (
    BasePaymentReconciliationSpec,
    PaymentReconciliationReadSpec,
    PaymentReconciliationRetrieveSpec,
    PaymentReconciliationStatusOptions,
    PaymentReconciliationWriteSpec,
)
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.lock import ObjectLocked
from care.utils.shortcuts import get_object_or_404
from care.utils.time_util import care_now


class PaymentReconciliationCancelRequest(BaseModel):
    reason: PaymentReconciliationStatusOptions


class PaymentReconciliationFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    target_invoice = filters.UUIDFilter(field_name="target_invoice__external_id")
    reconciliation_type = filters.CharFilter(lookup_expr="iexact")
    account = filters.UUIDFilter(field_name="account__external_id")
    is_credit_note = filters.BooleanFilter(field_name="is_credit_note")
    location = filters.UUIDFilter(field_name="location__external_id")
    method = filters.CharFilter(lookup_expr="iexact")
    created_by = filters.UUIDFilter(field_name="created_by__external_id")
    created_date = filters.DateTimeFromToRangeFilter(field_name="created_date")


class PaymentReconciliationAccountChangeRequest(BaseModel):
    payment_reconciliations: list[UUID4] = Field(min_length=1, max_length=100)
    target_account: UUID4


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
    pydantic_retrieve_model = PaymentReconciliationRetrieveSpec
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
        rebalance_account_task(instance.account.id)

    def handle_update(self, instance, request_data):
        account_id = instance.account_id
        with AccountLock(instance.account):
            instance.refresh_from_db()
            if instance.account_id != account_id:
                raise ObjectLocked
            return super().handle_update(instance, request_data)

    def validate_data(self, instance, model_obj=None):
        if model_obj and model_obj.status != instance.status:
            if instance.status in [
                PaymentReconciliationStatusOptions.cancelled.value,
                PaymentReconciliationStatusOptions.entered_in_error.value,
            ]:
                raise ValidationError(
                    "Cannot update payment reconciliation, use the cancel endpoint instead"
                )
            if model_obj.status in [
                PaymentReconciliationStatusOptions.cancelled.value,
                PaymentReconciliationStatusOptions.entered_in_error.value,
            ]:
                raise ValidationError(
                    "Payment reconciliation is already cancelled or entered in error"
                )
        return super().validate_data(instance, model_obj)

    def perform_update(self, instance):
        super().perform_update(instance)
        rebalance_account_task(instance.account.id)

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
        if instance.location:
            location = get_object_or_404(
                FacilityLocation, external_id=instance.location
            )
            if location.facility != facility:
                raise ValidationError("Location is not associated with the facility")
            if not AuthorizationController.call(
                "can_list_facility_location_obj", self.request.user, facility, location
            ):
                raise PermissionDenied("You do not have permission to given location")

        if instance.target_invoice:
            invoice = get_object_or_404(
                Invoice, external_id=instance.target_invoice, account=account
            )
            if invoice.facility != facility:
                raise ValidationError("Invoice is not associated with the facility")

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_write_payment_reconciliation_in_facility",
            self.request.user,
            model_instance.facility,
        ):
            raise PermissionDenied("Cannot update payment reconciliation")

    @action(methods=["POST"], detail=True)
    def cancel_payment_reconciliation(self, request, *args, **kwargs):
        request_data = PaymentReconciliationCancelRequest(**request.data)
        if request_data.reason not in [
            PaymentReconciliationStatusOptions.cancelled.value,
            PaymentReconciliationStatusOptions.entered_in_error.value,
        ]:
            raise ValidationError("Invalid reason")
        instance = self.get_object()
        account_id = instance.account_id
        with AccountLock(instance.account):
            instance.refresh_from_db()
            if instance.account_id != account_id:
                raise ObjectLocked
            if instance.created_date >= care_now() - timedelta(
                minutes=settings.PAYMENT_RECONCILIATION_FREE_CANCEL_PERIOD_MINUTES
            ):
                self.authorize_update({}, instance)
            elif not AuthorizationController.call(
                "can_destroy_payment_reconciliation_in_facility",
                self.request.user,
                instance.facility,
            ):
                raise PermissionDenied(
                    "User does not have permission to cancel payment reconciliation"
                )
            instance.status = request_data.reason
            instance.updated_by = self.request.user
            instance.save(update_fields=["status", "updated_by", "modified_date"])
            rebalance_account_task(instance.account.id)
            return Response(PaymentReconciliationReadSpec.serialize(instance).to_json())

    @extend_schema(
        request=PaymentReconciliationAccountChangeRequest,
    )
    @action(methods=["POST"], detail=False)
    def change_account(self, request, *args, **kwargs):
        facility = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_write_payment_reconciliation_in_facility",
            self.request.user,
            facility,
        ):
            raise PermissionDenied("Access Denied to Charge Item")
        request_params = PaymentReconciliationAccountChangeRequest(**request.data)
        target_account = get_object_or_404(
            Account, external_id=request_params.target_account, facility=facility
        )
        payment_ids = set(request_params.payment_reconciliations)
        queryset = PaymentReconciliation.objects.filter(
            external_id__in=payment_ids,
            facility=facility,
        )
        payments = list(queryset)
        if len(payments) != len(payment_ids):
            raise Http404("No PaymentReconciliation matches the given query.")
        original_accounts = {item.id: item.account_id for item in payments}
        account_ids = {target_account.id, *original_accounts.values()}
        accounts = list(Account.objects.filter(id__in=account_ids))
        with AccountLock(accounts):
            payments = list(queryset.all())
            if len(payments) != len(payment_ids):
                raise Http404("No PaymentReconciliation matches the given query.")
            for payment_reconciliation in payments:
                if (
                    payment_reconciliation.account_id
                    != original_accounts[payment_reconciliation.id]
                ):
                    raise ObjectLocked
                if payment_reconciliation.status not in [
                    PaymentReconciliationStatusOptions.active.value,
                    PaymentReconciliationStatusOptions.draft.value,
                ]:
                    raise ValidationError(
                        {"payment_reconciliation": "Not in Active Status"}
                    )
                if payment_reconciliation.target_invoice:
                    raise ValidationError(
                        {
                            "payment_reconciliation": "Cannot change account for a payment reconciliation against an invoice"
                        }
                    )
                payment_reconciliation.account = target_account
                payment_reconciliation.updated_by = request.user
                payment_reconciliation.save(
                    update_fields=["account", "updated_by", "modified_date"]
                )

            for account_id in account_ids:
                rebalance_account_task(account_id)
        return Response({}, status=status.HTTP_201_CREATED)
