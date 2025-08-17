from care.emr.models.patient import PatientIdentifier, PatientIdentifierConfig
from care.emr.utils.expression_evaluator import evaluate_expression
from care.utils.time_util import care_now


def evaluate_patient_default_expression(config, expression: str):
    context = {
        "patient_count": PatientIdentifier.objects.filter(
            config=config,
        ).count(),
        "current_year_yyyy": care_now().year,
        "current_year_yy": care_now().year % 100,
    }
    return evaluate_expression(expression, context)


def evaluate_patient_dummy_expression(expression):
    dummy_context = {
        "patient_count": 100,
        "current_year_yyyy": 2025,
        "current_year_yy": 25,
    }
    return evaluate_expression(expression, dummy_context)


def evaluate_patient_instance_default_values(patient):
    for config in PatientIdentifierConfig.objects.filter(
        facility=None, status="active"
    ).exclude(id__in=PatientIdentifier.objects.filter(patient=patient).values("id")):
        if config.config.get("default_value"):
            PatientIdentifier.objects.create(
                patient=patient,
                config=config,
                value=evaluate_patient_default_expression(
                    config, config.config.get("default_value")
                ),
            )
