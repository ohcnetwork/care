from care.emr.models.charge_item import ChargeItem
from care.emr.models.facility_config import FacilityMonetoryConfig
from care.emr.models.resource_category import merge_monetary_components
from care.emr.resources.account.default_account import get_default_account
from care.emr.resources.charge_item.spec import ChargeItemStatusOptions
from care.emr.resources.charge_item.sync_charge_item_costs import sync_charge_item_costs
from care.utils.evaluators.interpretation_evaluator import InterpretationEvaluator
from care.utils.rounding.covert_type import convert_to_decimal


def generate_negative_charge_item_definition(components):
    for component in components:
        if component.get("amount"):
            component["amount"] = str(-convert_to_decimal(component["amount"]))
    return components


def compute_global_components(charge_item_definition, price_components):
    facility = charge_item_definition.facility
    components_override = FacilityMonetoryConfig.get_monetory_component(facility.id)
    price_components_new = []
    for component in price_components:
        if component.get("global_component", None):
            component_key = FacilityMonetoryConfig.get_component_key(component)
            if component_key in components_override:
                price_components_new.append(components_override[component_key])
            else:
                price_components_new.append(component)
        else:
            price_components_new.append(component)
    return price_components_new


def compute_discount_configuration(charge_item_definition):
    discount_configuration = charge_item_definition.discount_configuration
    if discount_configuration:
        return discount_configuration
    return FacilityMonetoryConfig.get_discount_configuration(
        charge_item_definition.facility_id
    )


def apply_charge_item_definition(
    charge_item_definition,
    patient,
    facility,
    encounter=None,
    account=None,
    quantity=None,
    reverse=None,
    negative_allowed=False,
):
    if not account:
        account = get_default_account(patient, facility)
    if not quantity:
        quantity = 1.0
    context = {"patient": patient, "facility": facility}
    if encounter:
        context["encounter"] = encounter
    selected_components = []
    metrics_cache = {}
    price_components = charge_item_definition.price_components
    if charge_item_definition.category:
        price_components = merge_monetary_components(
            charge_item_definition.category.calculated_monetary_components,
            price_components,
        )
    price_components = compute_global_components(
        charge_item_definition, price_components
    )
    for component in price_components:
        if component.get("conditions"):
            evaluator = InterpretationEvaluator({}, metrics_cache)
            conditions_met = evaluator.evaluate_conditions(
                component.get("conditions"), context
            )
            metrics_cache = evaluator.metric_cache

            if not conditions_met:
                continue
        selected_components.append(component)
    if reverse:
        price_components = generate_negative_charge_item_definition(price_components)
    charge_item = ChargeItem(
        facility=facility,
        title=charge_item_definition.title,
        description=charge_item_definition.description,
        patient=patient,
        encounter=encounter,
        charge_item_definition=charge_item_definition,
        account=account,
        status=ChargeItemStatusOptions.billable.value,
        quantity=quantity,
        unit_price_components=selected_components,
        discount_configuration=compute_discount_configuration(charge_item_definition),
    )
    sync_charge_item_costs(charge_item, reverse=reverse or negative_allowed)
    return charge_item
