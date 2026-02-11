class FieldTypeRegistry:
    _types: dict[str, dict] = {}

    @classmethod
    def register(cls, type_name: str, schema: dict):
        cls._types[type_name] = schema

    @classmethod
    def get(cls, type_name: str) -> dict | None:
        return cls._types.get(type_name)

    @classmethod
    def get_all(cls) -> dict[str, dict]:
        return cls._types.copy()

    @classmethod
    def is_registered(cls, type_name: str) -> bool:
        return type_name in cls._types

    @classmethod
    def clear(cls):
        cls._types.clear()
