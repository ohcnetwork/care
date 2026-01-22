from rest_framework.exceptions import ValidationError

from care.emr.resources.common.monetary_component import (
    MonetaryComponents,
    MonetaryComponentType,
)
from care.utils.rounding.covert_type import convert_to_decimal
from care.utils.rounding.rounding import care_round


def calculate_amount(component, quantity, base):
    if component.amount:
        component.amount = convert_to_decimal(component.amount)
        component.amount = care_round(component.amount * quantity)
        return component
    if component.factor:
        component.factor = convert_to_decimal(component.factor)
        component.amount = care_round(base * component.factor / 100)
        return component
    raise ValidationError("Amount or factor is required")


def sync_charge_item_costs(charge_item, reverse=None):
    """
    Calculate total cost of charge item based on quantity and other factors
    """
    charge_item_price_components = MonetaryComponents(charge_item.unit_price_components)
    quantity = convert_to_decimal(charge_item.quantity)
    components = []
    total_price = 0
    base = 0
    for component in charge_item_price_components:
        if component.monetary_component_type == MonetaryComponentType.base.value:
            component.amount = care_round(
                convert_to_decimal(component.amount) * quantity
            )
            total_price = component.amount
            base = component.amount
            components.append(component.model_dump(mode="json", exclude_defaults=True))
    for component in charge_item_price_components:
        if component.monetary_component_type == MonetaryComponentType.surcharge.value:
            _component = calculate_amount(component, quantity, base)
            total_price += _component.amount
            components.append(_component.model_dump(mode="json", exclude_defaults=True))
    net_price = total_price
    for component in charge_item_price_components:
        if component.monetary_component_type == MonetaryComponentType.discount.value:
            _component = calculate_amount(component, quantity, net_price)
            total_price -= _component.amount
            components.append(_component.model_dump(mode="json", exclude_defaults=True))
    taxable_price = net_price
    for component in charge_item_price_components:
        if component.monetary_component_type == MonetaryComponentType.tax.value:
            _component = calculate_amount(component, quantity, taxable_price)
            total_price += _component.amount
            components.append(_component.model_dump(mode="json", exclude_defaults=True))
    charge_item.total_price = total_price
    charge_item.total_price_components = components
    if charge_item.total_price < 0 and not reverse:
        raise ValidationError("Total price is less than 0")
