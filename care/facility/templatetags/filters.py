from datetime import datetime

from django.template import Library

register = Library()


@register.filter(name="suggestion_string")
def suggestion_string(suggestion_code: str):
    if suggestion_code == "A":
        return "Admission"
    if suggestion_code == "HI":
        return "Home Isolation"
    if suggestion_code == "R":
        return "Referral"
    if suggestion_code == "OP":
        return "OP Consultation"
    if suggestion_code == "DC":
        return "Domiciliary Care"
    return "Other"


@register.filter()
def field_name_to_label(value):
    if value:
        return value.replace("_", " ").capitalize()
    return None


@register.filter(expects_localtime=True)
def parse_datetime(value):
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M")  # noqa: DTZ007
    except ValueError:
        return None
