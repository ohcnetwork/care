class ActionContextRegistry:
    _contexts = {}

    @classmethod
    def register(cls, context) -> None:
        cls._contexts[context.context_type] = context

    @classmethod
    def get_context(cls, context_type: str) -> any:
        if context_type in cls._contexts:
            return cls._contexts[context_type]
        return None
