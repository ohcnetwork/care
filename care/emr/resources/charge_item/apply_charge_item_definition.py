from care.emr.models.charge_item import ChargeItem
from care.emr.resources.account.default_account import get_default_account
from care.emr.resources.charge_item.spec import ChargeItemStatusOptions
from care.emr.resources.charge_item.sync_charge_item_costs import sync_charge_item_costs
from care.utils.evaluators.interpretation_evaluator import InterpretationEvaluator


def apply_charge_item_definition(
    charge_item_definition,
    patient,
    facility,
    encounter=None,
    account=None,
    quantity=None,
):
    if not account:
        account = get_default_account(patient, facility)
    if not quantity:
        quantity = 1.0
    context = {"patient": patient}
    if encounter:
        context["encounter"] = encounter
    selected_components = []
    metrics_cache = {}
    price_components = charge_item_definition.price_components
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
    )
    sync_charge_item_costs(charge_item)
    return charge_item
