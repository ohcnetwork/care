from decimal import Decimal


def convert_to_decimal(value: Decimal | float | str | int | None) -> Decimal | None:
    """
    Convert a value to Decimal correctly.
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)
