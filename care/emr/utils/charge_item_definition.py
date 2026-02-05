from care.emr.models.activity_definition import ActivityDefinition
from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.product import Product
from care.emr.models.scheduling.schedule import Schedule


def is_linked_to_any_resource(charge_item_def_id: int) -> bool:
    if Product.objects.filter(charge_item_definition_id=charge_item_def_id).exists():
        return True

    if Schedule.objects.filter(charge_item_definition_id=charge_item_def_id).exists():
        return True

    if Schedule.objects.filter(
        revisit_charge_item_definition_id=charge_item_def_id
    ).exists():
        return True

    return ActivityDefinition.objects.filter(
        charge_item_definitions__contains=[charge_item_def_id]
    ).exists()


def recalculate_separately_billable(charge_item_def_id: int) -> None:
    try:
        charge_item_def = ChargeItemDefinition.objects.get(id=charge_item_def_id)
    except ChargeItemDefinition.DoesNotExist:
        return

    is_linked = is_linked_to_any_resource(charge_item_def_id)
    new_value = not is_linked

    if charge_item_def.separately_billable != new_value:
        charge_item_def.separately_billable = new_value
        charge_item_def.save(update_fields=["separately_billable"])


def set_separately_billable_false(charge_item_def_id: int) -> None:
    ChargeItemDefinition.objects.filter(id=charge_item_def_id).update(
        separately_billable=False
    )
