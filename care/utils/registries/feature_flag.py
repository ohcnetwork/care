import enum
import logging

from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class FlagNotFoundException(ValidationError):
    pass


class FlagType(enum.Enum):
    USER = "USER"
    FACILITY = "FACILITY"


# TODO: convert to type in python 3.12
FlagName = str
type FlagTypeRegistry = dict[FlagType, dict[FlagName, bool]]


class FlagRegistry:
    _flags: FlagTypeRegistry = {}

    @classmethod
    def register(cls, flag_type: FlagType, flag_name: FlagName) -> None:
        if flag_type not in cls._flags:
            cls._flags[flag_type] = {}
        cls._flags[flag_type][flag_name] = True

    @classmethod
    def unregister(cls, flag_type, flag_name) -> None:
        try:
            del cls._flags[flag_type][flag_name]
        except KeyError as e:
            logger.warning(f"Flag {flag_name} not found in {flag_type}: {e}")

    @classmethod
    def register_wrapper(cls, flag_type, flag_name) -> None:
        def inner_wrapper(wrapped_class):
            cls.register(cls, flag_type, flag_name)
            return wrapped_class

        return inner_wrapper

    @classmethod
    def validate_flag_type(cls, flag_type: FlagType) -> None:
        if flag_type not in cls._flags:
            msg = "Invalid Flag Type"
            raise FlagNotFoundException(msg)

    @classmethod
    def validate_flag_name(cls, flag_type: FlagType, flag_name):
        cls.validate_flag_type(flag_type)
        if flag_name not in cls._flags[flag_type]:
            msg = "Flag not registered"
            raise FlagNotFoundException(msg)

    @classmethod
    def get_all_flags(cls, flag_type: FlagType) -> list[FlagName]:
        cls.validate_flag_type(flag_type)
        return list(cls._flags[flag_type].keys())

    @classmethod
    def get_all_flags_as_choices(
        cls, flag_type: FlagType
    ) -> list[tuple[FlagName, FlagName]]:
        return ((x, x) for x in cls._flags.get(flag_type, {}))
