from typing import Self
from uuid import UUID

from ulid import ULID as BaseULID


class ULID(BaseULID):
    @classmethod
    def parse(cls, value) -> Self:
        if isinstance(value, BaseULID):
            return value
        if isinstance(value, UUID):
            return cls.from_uuid(value)
        if isinstance(value, str):
            len_value = len(value)
            if len_value == 32 or len_value == 36:
                return cls.from_uuid(UUID(value))
            if len_value == 26:
                return cls.from_str(value)
            if len_value == 16:
                return cls.from_bytes(value)
            if len_value == 10:
                return cls.from_timestamp(int(value))
            raise ValueError(
                "Cannot create ULID from string of length {}".format(len_value)
            )
        if isinstance(value, (int, float)):
            return cls.from_int(int(value))
        if isinstance(value, (bytes, bytearray)):
            return cls.from_bytes(value)
        if isinstance(value, memoryview):
            return cls.from_bytes(value.tobytes())
        raise ValueError(
            "Cannot create ULID from type {}".format(value.__class__.__name__)
        )
