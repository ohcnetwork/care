from rest_framework.exceptions import ValidationError


def check_integer(vals):
    if not isinstance(vals, list):
        vals = [vals]
    for i in range(len(vals)):
        try:
            vals[i] = int(vals[i])
        except Exception:
            raise ValidationError({"value": "Integer Required"}) from None
    return vals
