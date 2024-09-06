import enum
from django.core.exceptions import ValidationError


class FlagNotFoundException(ValidationError):
    pass


class FlagType(enum.Enum):
    USER = "USER"
    FACILITY = "FACILITY"


class FlagRegistry:
    _flags = {}

    @classmethod
    def register(cls, flag_type, flag_name):
        if flag_type not in FlagType:
            return
        if flag_type not in cls._flags:
            cls._flags[flag_type] = {}
        cls._flags[flag_type][flag_name] = True  # Using a dict to avoid duplication ( sets are also fine )

    @classmethod
    def register_wrapper(cls, flag_type, flag_name):
        def inner_wrapper(wrapped_class):
            cls.register(cls, flag_type, flag_name)
            return wrapped_class

        return inner_wrapper

    @classmethod
    def validate_flag_type(cls, flag_type):
        if flag_type not in FlagType or flag_type not in cls._flags:
            raise FlagNotFoundException("Invalid Flag Type")

    @classmethod
    def get_all_flags(cls, flag_type: FlagType):
        cls.validate_flag_type(flag_type)
        return list(cls._flags[flag_type].keys())

    @classmethod
    def validate_flag_name(cls, flag_type, flag_name):
        cls.validate_flag_type(flag_type)
        if flag_name not in cls._flags[flag_type]:
            raise FlagNotFoundException("Flag not registered")

FlagRegistry.register(FlagType.FACILITY, "Test Flag") # To be Removed
