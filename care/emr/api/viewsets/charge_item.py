from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter

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
from care.emr.models.encounter import Encounter
from care.emr.models.service_request import ServiceRequest
from care.emr.registries.system_questionnaire.system_questionnaire import (
    InternalQuestionnaireRegistry,
)
from care.emr.resources.account.default_account import get_default_account
from care.emr.resources.charge_item.spec import (
    ChargeItemReadSpec,
    ChargeItemResourceOptions,
    ChargeItemSpec,
    ChargeItemWriteSpec,
)
from care.emr.resources.charge_item.sync_charge_item_costs import sync_charge_item_costs
from care.emr.resources.questionnaire.spec import SubjectType
from care.emr.resources.tag.config_spec import TagResource
from care.facility.models.facility import Facility


class ChargeItemDefinitionFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    title = filters.CharFilter(lookup_expr="icontains")
    account = filters.UUIDFilter(field_name="account__external_id")
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    service_resource = filters.CharFilter(lookup_expr="iexact")
    service_resource_id = filters.CharFilter(lookup_expr="iexact")


def validate_service_resource(service_resource, service_resource_id):
    # TODO : Add Authz
    try:
        if service_resource == ChargeItemResourceOptions.service_request.value:
            return ServiceRequest.objects.filter(
                external_id=service_resource_id
            ).exists()
    except Exception:
        return False
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
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering = [
        "-created_date",
    ]
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

    def validate_data(self, instance, model_obj=None):
        if instance.service_resource and not validate_service_resource(
            instance.service_resource, instance.service_resource_id
        ):
            raise ValidationError("Invalid service resource")
        return super().validate_data(instance, model_obj)

    def perform_create(self, instance):
        instance.facility = self.get_facility_obj()
        if not instance.account_id:
            instance.account = get_default_account(
                instance.patient, self.get_facility_obj()
            )
        sync_charge_item_costs(instance)
        super().perform_create(instance)

    def perform_update(self, instance):
        sync_charge_item_costs(instance)
        super().perform_update(instance)

    def authorize_create(self, instance):
        facility = self.get_facility_obj()
        encounter = get_object_or_404(Encounter, external_id=instance.encounter)
        if instance.account:
            account = get_object_or_404(
                Account, external_id=instance.account, encounter=encounter
            )
            if account.facility != facility:
                raise ValidationError("Account is not associated with the facility")
        # TODO: AuthZ pending
        return super().authorize_create(instance)

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("paid_invoice", "charge_item_definition")
        )


InternalQuestionnaireRegistry.register(ChargeItemViewSet)
