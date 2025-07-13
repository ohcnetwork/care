from care.emr.models.charge_item import ChargeItem
from care.emr.resources.account.default_account import get_default_account
from care.emr.resources.charge_item.spec import ChargeItemStatusOptions
from care.emr.resources.charge_item.sync_charge_item_costs import sync_charge_item_costs


def apply_charge_item_definition(
    charge_item_definition, encounter, account=None, quantity=None
):
    if not account:
        account = get_default_account(encounter.patient, encounter.facility)
    if not quantity:
        quantity = 1.0
    charge_item = ChargeItem(
        facility=encounter.facility,
        title=charge_item_definition.title,
        description=charge_item_definition.description,
        patient=encounter.patient,
        encounter=encounter,
        charge_item_definition=charge_item_definition,
        account=account,
        status=ChargeItemStatusOptions.billable.value,
        quantity=quantity,
        unit_price_components=charge_item_definition.price_components,
    )
    sync_charge_item_costs(charge_item)
    return charge_item
