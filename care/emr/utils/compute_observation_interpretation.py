import sentry_sdk
from rest_framework.exceptions import ValidationError

from care.utils.evaluators.interpretation_evaluator import InterpretationEvaluator


def compute_observation_interpretation(model_instance):
    """Helper method to compute interpretation for observation instances."""
    try:
        if not model_instance.component:
            evaluator = InterpretationEvaluator(
                model_instance.observation_definition.qualified_ranges
            )
            context = evaluator.build_patient_context(
                model_instance.patient, model_instance.effective_datetime
            )
            value_to_evaluate = evaluator.extract_value(model_instance.value)

            model_instance.interpretation = evaluator.evaluate(
                context, value_to_evaluate
            )
            matched_condition = evaluator.get_matching_condition(context)
            if matched_condition:
                model_instance.reference_range = matched_condition.get("ranges", [])
        else:
            component_definition_dict = {
                component_def["code"]["code"]: component_def["qualified_ranges"]
                for component_def in model_instance.observation_definition.component
            }

            for component in model_instance.component:
                component_code = component.get("code", {}).get("code")
                evaluator = InterpretationEvaluator(
                    component_definition_dict.get(component_code, [])
                )
                context = evaluator.build_patient_context(
                    model_instance.patient, model_instance.effective_datetime
                )
                component_value = evaluator.extract_value(component.get("value"))

                component["interpretation"] = evaluator.evaluate(
                    context, component_value
                )
                matched_condition = evaluator.get_matching_condition(context)
                if matched_condition:
                    component["reference_range"] = matched_condition.get("ranges", [])
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise ValidationError("Error computing interpretation") from e
