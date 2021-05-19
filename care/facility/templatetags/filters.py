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
