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


ROUNDING_CLASS = {}


def get_rounding_class(method):
    global ROUNDING_CLASS  # noqa: PLW0602
    if ROUNDING_CLASS.get(method) is not None and method is None:
        return ROUNDING_CLASS.get(method)
    module_name, _, class_name = method.rpartition(".")
    module = importlib.import_module(module_name)
    # Get the class from the module
    rounding_class = getattr(module, class_name)
    if not rounding_class:
        raise ValueError("Rounding class not found")
    ROUNDING_CLASS[method] = rounding_class
    return ROUNDING_CLASS[method]


def care_round(
    val1: Decimal,
    precision: int | None = None,
    method: str | None = None,
    care_method: str | None = None,
):
    if val1 is None:
        return Decimal(0)
    if not care_method:
        care_method = settings.ACCOUNTING_ROUNDING_METHOD
    rounding_class = get_rounding_class(care_method)
    return rounding_class.round(val1, precision, method)
