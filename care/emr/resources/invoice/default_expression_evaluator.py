from care.emr.models.invoice import Invoice
from care.emr.utils.expression_evaluator import evaluate_expression
from care.utils.time_util import care_now


def evaluate_invoice_identifier_default_expression(facility):
    context = {
        "invoice_count": Invoice.objects.filter(
            facility=facility,
        ).count(),
        "current_year_yyyy": care_now().year,
        "current_year_yy": care_now().year % 100,
    }
    if not facility.invoice_number_expression:
        return ""
    return evaluate_expression(facility.invoice_number_expression, context)


def evaluate_invoice_dummy_expression(expression):
    dummy_context = {
        "invoice_count": 1234,
        "current_year_yyyy": 2025,
        "current_year_yy": 25,
    }
    return evaluate_expression(expression, dummy_context)
