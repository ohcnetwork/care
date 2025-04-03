from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string


def get_sms_content(template_path: str, context: dict) -> str:
    try:
        return render_to_string(template_path, context)
    except TemplateDoesNotExist:
        error = f"Template '{template_path}' not found."
        raise TemplateDoesNotExist(error) from error
