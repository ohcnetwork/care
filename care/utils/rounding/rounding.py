import importlib
from decimal import (
    ROUND_05UP,
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_FLOOR,
    ROUND_HALF_DOWN,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    ROUND_UP,
    Decimal,
)

from django.conf import settings


class RoundingBase:
    ROUNDING_METHOD = ""

    @classmethod
    def round(
        cls, val1: Decimal, precision: int | None = None, method: str | None = None
    ):
        if precision is None:
            precision = settings.ACCOUNTING_PRECISION
        if method is None:
            method = cls.ROUNDING_METHOD
        return val1.quantize(Decimal(10) ** -precision, rounding=method)


class RoundingHalfUp(RoundingBase):
    ROUNDING_METHOD = ROUND_HALF_UP


class RoundingHalfDown(RoundingBase):
    ROUNDING_METHOD = ROUND_HALF_DOWN


class RoundingHalfEven(RoundingBase):
    ROUNDING_METHOD = ROUND_HALF_EVEN


class RoundingUp(RoundingBase):
    ROUNDING_METHOD = ROUND_UP


class RoundingDown(RoundingBase):
    ROUNDING_METHOD = ROUND_DOWN


class RoundingCeiling(RoundingBase):
    ROUNDING_METHOD = ROUND_CEILING


class RoundingFloor(RoundingBase):
    ROUNDING_METHOD = ROUND_FLOOR


class Rounding05Up(RoundingBase):
    ROUNDING_METHOD = ROUND_05UP


ROUNDING_CLASS = None


def get_rounding_class():
    global ROUNDING_CLASS  # noqa: PLW0603
    if ROUNDING_CLASS is not None:
        return ROUNDING_CLASS
    class_path = settings.ACCOUNTING_ROUNDING_METHOD
    module_name, _, class_name = class_path.rpartition(".")
    module = importlib.import_module(module_name)
    # Get the class from the module
    rounding_class = getattr(module, class_name)
    if not rounding_class:
        raise ValueError("Rounding class not found")
    ROUNDING_CLASS = rounding_class
    return ROUNDING_CLASS


def care_round(val1: Decimal, precision: int | None = None, method: str | None = None):
    if val1 is None:
        return Decimal(0)
    rounding_class = get_rounding_class()
    return rounding_class.round(val1, precision, method)
