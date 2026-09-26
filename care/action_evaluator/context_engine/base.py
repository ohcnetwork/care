class ActionContextBase:
    context_type: str

    def __init__(self, context_obj):
        self.context_obj = context_obj


class ActionContextFieldBase:
    context_type: ActionContextBase
    target_context_type: ActionContextBase | None
    field: str
    evaluation: str

    def __init__(self, request, user, context_obj, field_cache, context_cache) -> None:
        self.context_obj = context_obj.context_obj
        self.field_cache = field_cache
        self.context_cache = context_cache
        self.request = request
        self.user = user

    def get_context_value(self) -> any:
        raise NotImplementedError("get_context_value is not implemented")

    @classmethod
    def render_dict(cls) -> dict:
        response = {
            "context_type": cls.context_type.context_type,
            "field": cls.field,
            "evaluation": cls.evaluation,
        }
        if getattr(cls, "target_context_type", None):
            response["target_context_type"] = cls.target_context_type.context_type
        return response


class StaticActionContextBase(ActionContextFieldBase):
    evaluation = "static"


class GlobalActionContextBase(ActionContextFieldBase):
    evaluation = "global"


class DynamicActionContextBase(ActionContextFieldBase):
    evaluation = "dynamic"
    field = None

    def get_context_value(self, field):
        raise NotImplementedError("get_context_value is not implemented")
