from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
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
from care.emr.resources.account.spec import (
    AccountBillingStatusOptions,
    AccountCreateSpec,
    AccountReadSpec,
    AccountRetrieveSpec,
    AccountSpec,
    AccountStatusOptions,
)
from care.emr.resources.account.sync_items import sync_account_items
from care.facility.models.facility import Facility


class AccountFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    name = filters.CharFilter(lookup_expr="icontains")
    billing_status = filters.CharFilter(lookup_expr="iexact")
    patient = filters.UUIDFilter(field_name="patient__external_id")


class AccountViewSet(
    EMRCreateMixin, EMRRetrieveMixin, EMRUpdateMixin, EMRListMixin, EMRBaseViewSet
):
    database_model = Account
    pydantic_model = AccountCreateSpec
    pydantic_update_model = AccountSpec
    pydantic_read_model = AccountReadSpec
    pydantic_retrieve_model = AccountRetrieveSpec
    filterset_class = AccountFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def get_facility_obj(self):
        return get_object_or_404(
            Facility,
            external_id=self.kwargs["facility_external_id"],
        )

    def validate_data(self, instance, model_obj=None):
        patient = model_obj.patient.external_id if model_obj else instance.patient
        qs = Account.objects.filter(
            facility=self.get_facility_obj(),
            patient__external_id=patient,
        )
        if model_obj:
            qs = qs.exclude(id=model_obj.id)
        if (
            instance.status == AccountStatusOptions.active.value
            and instance.billing_status == AccountBillingStatusOptions.open.value
        ) and qs.filter(
            status=AccountStatusOptions.active.value,
            billing_status=AccountBillingStatusOptions.open.value,
        ).exists():
            err = "Active account already exists for this patient"
            raise ValidationError(err)

        return super().validate_data(instance, model_obj)

    def perform_create(self, instance):
        instance.facility = self.get_facility_obj()
        instance.save()
        return instance

    @action(methods=["POST"], detail=True)
    def rebalance(self, request, *args, **kwargs):
        account = self.get_object()
        sync_account_items(account)
        account.save()
        return Response(AccountRetrieveSpec.serialize(account).to_json())

    def get_queryset(self):
        return super().get_queryset().filter(facility=self.get_facility_obj())
