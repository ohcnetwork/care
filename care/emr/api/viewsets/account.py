from django_filters import rest_framework as filters
from pydantic import UUID4, BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRTagMixin,
    EMRUpdateMixin,
)
from care.emr.models.account import Account
from care.emr.models.encounter import Encounter
from care.emr.models.patient import Patient
from care.emr.resources.account.spec import (
    AccountBillingStatusOptions,
    AccountCreateSpec,
    AccountReadSpec,
    AccountRetrieveSpec,
    AccountStatusOptions,
    AccountUpdateSpec,
)
from care.emr.resources.account.sync_items import sync_account_items
from care.emr.resources.tag.config_spec import TagResource
from care.emr.tagging.filters import SingleFacilityTagFilter
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404


class AccountFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    name = filters.CharFilter(lookup_expr="icontains")
    billing_status = filters.CharFilter(lookup_expr="iexact")
    patient = filters.UUIDFilter(field_name="patient__external_id")
    created_date = filters.DateTimeFromToRangeFilter(field_name="created_date")
    encounter = filters.UUIDFilter(field_name="primary_encounter__external_id")


class AccountSetPrimaryEncounterSpec(BaseModel):
    patient: UUID4
    facility: UUID4
    encounter: UUID4


class AccountViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRTagMixin,
    EMRBaseViewSet,
):
    database_model = Account
    pydantic_model = AccountCreateSpec
    pydantic_update_model = AccountUpdateSpec
    pydantic_read_model = AccountReadSpec
    pydantic_retrieve_model = AccountRetrieveSpec
    filterset_class = AccountFilters
    filter_backends = [
        filters.DjangoFilterBackend,
        OrderingFilter,
        SearchFilter,
        SingleFacilityTagFilter,
    ]
    search_fields = ["name"]
    ordering_fields = ["created_date", "modified_date"]
    resource_type = TagResource.account

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

    def authorize_create(self, instance):
        if not AuthorizationController.call(
            "can_create_account_in_facility",
            self.request.user,
            self.get_facility_obj(),
        ):
            raise PermissionDenied("You are not authorized to create accounts")

    def authorize_update(self, request_obj, model_instance):
        if getattr(request_obj, "primary_encounter", None):
            encounter = get_object_or_404(
                Encounter, external_id=request_obj.primary_encounter
            )
            if encounter.facility != model_instance.facility:
                raise PermissionDenied(
                    "Primary encounter is not associated with the facility"
                )
            if encounter.patient != model_instance.patient:
                raise PermissionDenied(
                    "Primary encounter is not associated with the patient"
                )
            if (
                Account.objects.exclude(id=model_instance.id)
                .filter(primary_encounter=encounter)
                .exists()
            ):
                raise PermissionDenied(
                    "Encounter is already associated with an account"
                )
        if not AuthorizationController.call(
            "can_update_account_in_facility",
            self.request.user,
            model_instance.facility,
        ):
            raise PermissionDenied("You are not authorized to update accounts")

    @action(methods=["POST"], detail=False)
    def default_account(self, request, *args, **kwargs):
        request_data = AccountSetPrimaryEncounterSpec(**request.data)
        patient = get_object_or_404(
            Patient.objects.only("id"), external_id=request_data.patient
        )
        facility = get_object_or_404(
            Facility.objects.only("id"), external_id=request_data.facility
        )
        encounter = get_object_or_404(
            Encounter.objects.only("id"), external_id=request_data.encounter
        )
        self.authorize_read(facility)
        if encounter.facility != facility:
            raise PermissionDenied("Encounter is not associated with the facility")
        if encounter.patient != patient:
            raise PermissionDenied("Encounter is not associated with the patient")
        encounter_account = Account.objects.filter(
            patient=patient, facility=facility, primary_encounter=encounter
        ).first()
        if encounter_account:
            account = encounter_account
        else:
            account = Account.objects.filter(
                patient=patient,
                facility=facility,
                status=AccountStatusOptions.active.value,
                billing_status=AccountBillingStatusOptions.open.value,
            ).first()
        if not account:
            raise ValidationError("No account found")
        return Response(AccountRetrieveSpec.serialize(account).to_json())

    @action(methods=["POST"], detail=True)
    def rebalance(self, request, *args, **kwargs):
        account = self.get_object()
        self.authorize_update({}, account)
        sync_account_items(account)
        account.save()
        return Response(AccountRetrieveSpec.serialize(account).to_json())

    def authorize_read(self, facility):
        if not AuthorizationController.call(
            "can_read_account_in_facility",
            self.request.user,
            facility,
        ):
            raise PermissionDenied("You are not authorized to read accounts")

    def get_queryset(self):
        facility = self.get_facility_obj()
        self.authorize_read(facility)
        return super().get_queryset().filter(facility=facility)
