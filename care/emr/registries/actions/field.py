class ActionFieldRegistry:
    _contexts = {}
    _global_fields = {}
    _dynamic_contexts = {}

    @classmethod
    def register(cls, field) -> None:
        context_type = field.context_type.context_type
        if field.evaluation == "dynamic":
            if context_type not in cls._dynamic_contexts:
                cls._dynamic_contexts[context_type] = []
            cls._dynamic_contexts[context_type].append(field)
            return
        if context_type not in cls._contexts:
            cls._contexts[context_type] = {}
        if field.field == "self":
            raise ValueError("Self field is not allowed")
        cls._global_fields[field.field] = field
        cls._contexts[context_type][field.field] = field

    @classmethod
    def get_static_field(cls, context_type: str, field: str) -> bool:
        if context_type in cls._contexts and field in cls._contexts[context_type]:
            return cls._contexts[context_type][field]
        return None

    @classmethod
    def get_global_field(cls, field: str) -> bool:
        if field in cls._global_fields:
            return cls._global_fields[field]
        return None

    @classmethod
    def get_dynamic_contexts(cls, context_type: str) -> list:
        if context_type in cls._dynamic_contexts:
            return cls._dynamic_contexts[context_type]
        return []
