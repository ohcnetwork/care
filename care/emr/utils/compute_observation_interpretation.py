from care.utils.evaluators.interpretation_evaluator import InterpretationEvaluator


def compute_observation_interpretation(model_instance, metrics_cache):
    """Helper method to compute interpretation for observation instances."""
    evaluation_context = {
        "patient": model_instance.patient,
    }
    try:
        evaluator = InterpretationEvaluator(
            model_instance.observation_definition.qualified_ranges, metrics_cache
        )

        interpretation, ranges = evaluator.evaluate(
            evaluation_context, model_instance.value
        )
        if interpretation:
            model_instance.interpretation = interpretation
            model_instance.reference_range = ranges
        metrics_cache = evaluator.metric_cache
        # Handle Components
        if not model_instance.observation_definition.component:
            return None
        component_definition_dict = {
            component_def.get("code", {}).get("code"): component_def.get(
                "qualified_ranges"
            )
            for component_def in model_instance.observation_definition.component
        }

        for component in model_instance.component:
            component_code = component.get("code", {}).get("code")
            if not component_code or not component_definition_dict.get(component_code):
                continue
            evaluator = InterpretationEvaluator(
                component_definition_dict.get(component_code, [])
            )

            interpretation, ranges = evaluator.evaluate(
                evaluation_context, component.get("value")
            )
            if interpretation:
                component["interpretation"] = interpretation
                component["reference_range"] = ranges
            metrics_cache = evaluator.metric_cache
    except Exception as e:
        raise e
    return metrics_cache
