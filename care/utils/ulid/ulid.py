from typing import Self
from uuid import UUID

from ulid import ULID as BaseULID  # noqa: N811

UUID_LEN_WITHOUT_HYPHENS = 32
UUID_LEN_WITH_HYPHENS = 36
ULID_STR_LEN = 26
ULID_BYTES_LEN = 16
TIMESTAMP_STR_LEN = 10


class ULID(BaseULID):
    @classmethod
    def parse(cls, value) -> Self:
        if isinstance(value, BaseULID):
            return cls.parse_ulid(value)
        if isinstance(value, UUID):
            return cls.parse_uuid(value)
        if isinstance(value, str):
            return cls.parse_str(value)
        if isinstance(value, int | float):
            return cls.parse_int_float(value)
        if isinstance(value, bytes | bytearray):
            return cls.parse_bytes(value)
        if isinstance(value, memoryview):
            return cls.parse_memoryview(value)
        msg = f"Cannot create ULID from type {value.__class__.__name__}"
        raise ValueError(msg)

    @classmethod
    def parse_ulid(cls, value: BaseULID) -> Self:
        return value

    @classmethod
    def parse_uuid(cls, value: UUID) -> Self:
        return cls.from_uuid(value)

    @classmethod
    def parse_str(cls, value: str) -> Self:
        len_value = len(value)
        if len_value in (UUID_LEN_WITHOUT_HYPHENS, UUID_LEN_WITH_HYPHENS):
            return cls.from_uuid(UUID(value))
        if len_value == ULID_STR_LEN:
            return cls.from_str(value)
        if len_value == ULID_BYTES_LEN:
            return cls.from_bytes(value.encode())
        if len_value == TIMESTAMP_STR_LEN:
            return cls.from_timestamp(int(value))
        msg = f"Cannot create ULID from string of length {len_value}"
        raise ValueError(msg)

    @classmethod
    def parse_int_float(cls, value: int | float) -> Self:
        return cls.from_int(int(value))

    @classmethod
    def parse_bytes(cls, value: bytes | bytearray) -> Self:
        return cls.from_bytes(value)

    @classmethod
    def parse_memoryview(cls, value: memoryview) -> Self:
        return cls.from_bytes(value.tobytes())
