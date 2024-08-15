from django import template

register = template.Library()


@register.filter(name="format_empty_data")
def format_empty_data(data):
    if data is None or data == "" or data == 0.0 or data == []:
        return "N/A"

    return data


@register.filter(name="format_to_sentence_case")
def format_to_sentence_case(data):
    if data is None:
        return

    def convert_to_sentence_case(s):
        s = s.lower()
        s = s.replace("_", " ")
        return s.capitalize()

    if isinstance(data, str):
        items = data.split(", ")
        converted_items = [convert_to_sentence_case(item) for item in items]
        return ", ".join(converted_items)

    elif isinstance(data, (list, tuple)):
        converted_items = [convert_to_sentence_case(item) for item in data]
        return ", ".join(converted_items)

    return data
