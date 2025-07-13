"""
Defines how an ActivityDefinition is converted into a ServiceRequest
"""

from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.service_request import ServiceRequest
from care.emr.resources.account.default_account import get_default_account
from care.emr.resources.charge_item.apply_charge_item_definition import (
    apply_charge_item_definition,
)
from care.emr.resources.charge_item.spec import ChargeItemResourceOptions
from care.emr.resources.service_request.spec import (
    ServiceRequestIntentChoices,
    ServiceRequestPriorityChoices,
    ServiceRequestStatusChoices,
)


def convert_ad_to_sr(activity_definition, encounter):
    return ServiceRequest(
        facility=activity_definition.facility,
        title=activity_definition.title,
        category=activity_definition.category,
        status=ServiceRequestStatusChoices.draft.value,
        intent=ServiceRequestIntentChoices.proposal.value,
        priority=ServiceRequestPriorityChoices.routine.value,
        do_not_perform=False,
        note=None,
        occurance=None,
        patient_instruction=None,
        code=activity_definition.code,
        body_site=activity_definition.body_site,
        locations=activity_definition.locations,
        patient=encounter.patient,
        encounter=encounter,
        healthcare_service=activity_definition.healthcare_service,
    )


def apply_ad_charge_definitions(activity_definition, encounter, service_request):
    charge_item_definitions = ChargeItemDefinition.objects.filter(
        id__in=activity_definition.charge_item_definitions
    )
    account = get_default_account(encounter.patient, service_request.facility)
    for charge_item_definition in charge_item_definitions:
        charge_item = apply_charge_item_definition(
            charge_item_definition, encounter, account
        )
        charge_item.service_resource = ChargeItemResourceOptions.service_request.value
        charge_item.service_resource_id = str(service_request.external_id)
        charge_item.save()
    return service_request
