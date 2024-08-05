from django import template

register = template.Library()


@register.filter(name="format_empty_data")
def format_empty_data(data):
    if data is None or data == "" or data == 0.0:
        return "N/A"

    return data
