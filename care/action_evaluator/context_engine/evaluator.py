from care.action_evaluator.context_engine.base import ActionContextBase
from care.emr.registries.actions.context import ActionContextRegistry
from care.emr.registries.actions.field import ActionFieldRegistry


class ActionContextEvaluator:
    """
    Go through the contexts available and evaluate the variable
    """

    def __init__(self, request, user, field_cache, context_cache, cache):
        self.request = request
        self.user = user
        self.field_cache = field_cache
        self.context_cache = context_cache
        self.cache = cache

    def evaluate(  # noqa : PLR0912
        self,
        field: str,
        context_type: str,
        context_obj: any,
        context_mode: bool = False,
    ) -> any:
        if not context_mode and field in self.field_cache:
            return self.field_cache[field]
        if context_mode and field in self.context_cache:
            return self.context_cache[field]
        fields = field.split(".")
        context_object = ActionContextRegistry.get_context(context_type)(context_obj)
        result = None
        cache = self.field_cache if not context_mode else self.context_cache
        part_field = None
        for index, part_field in enumerate(fields):
            if len(fields) > 1 and index != len(fields) - 1:
                if part_field not in cache:
                    cache[part_field] = {}
                cache = cache[part_field]
            if result is not None:
                context_object = result
            context = ActionFieldRegistry.get_static_field(
                context_object.context_type, part_field
            )
            if not context:
                context = ActionFieldRegistry.get_global_field(part_field)
            if not isinstance(context_object, ActionContextBase):
                raise ValueError(
                    "Context object is not a subclass of ActionContextBase"
                )
            if context:
                result = context(
                    self.request,
                    self.user,
                    context_object,
                    self.field_cache,
                    self.context_cache,
                ).get_context_value()
                continue
            contexts = ActionFieldRegistry.get_dynamic_contexts(
                context_object.context_type
            )
            if contexts:
                for context in contexts:
                    result = context(
                        self.request,
                        self.user,
                        context_object,
                        self.field_cache,
                        self.context_cache,
                    ).get_context_value(field)
                    if result is not None:
                        break
                if result is not None:
                    continue
            err = f"No context value found for field {field}"
            raise ValueError(err)
        if not context_mode:
            cache[part_field] = result
            self.field_cache[field] = result
        if context_mode:
            cache[part_field] = result
            self.context_cache[field] = result
        return result
