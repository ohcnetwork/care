from typing import Any

from django.db import models


def sort_index(field_name: str, order: list[Any] | None) -> models.Case:
    """
    Creates a Case expression that can be used to sort a queryset based on a specified order list.

    This function is useful for ordering QuerySet results to match a predefined sequence.
    For example, to display certain items first in a specific order.

    Args:
        field_name: The name of the model field to compare against values in the order list.
        order: A list of values to be used for ordering. Records with field values matching
              items in this list will be ordered according to their position in the list.
              If None or empty, returns an empty Case that won't affect ordering.

    Returns:
        A Django Case expression that can be used in QuerySet.annotate() or order_by().

    Examples:
        # Sort patients by priority status: ['critical', 'urgent', 'stable']
        patients = Patient.objects.annotate(
            priority_order=sort_index('status', ['critical', 'urgent', 'stable'])
        ).order_by('priority_order')
    """
    if not order:
        return models.Value(0, output_field=models.IntegerField())

    if not isinstance(order, list):
        raise TypeError("order must be a list")

    return models.Case(
        *[
            models.When(**{field_name: value}, then=pos)
            for pos, value in enumerate(order)
        ],
        # no matches will be sorted after all matched items
        default=len(order),
        output_field=models.IntegerField(),
    )
