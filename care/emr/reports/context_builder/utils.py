from datetime import date, datetime


def format_date(value, format_str="%d/%m/%Y"):
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    if isinstance(value, (datetime, date)):
        return value.strftime(format_str)
    return str(value)


def format_datetime(value, format_str="%d/%m/%Y %I:%M %p"):
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    if isinstance(value, datetime):
        return value.strftime(format_str)
    return str(value)


def format_phone_number(phone):
    if not phone:
        return ""
    phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if phone.startswith("+91"):
        return f"+91 {phone[3:8]} {phone[8:]}"
    if len(phone) == 10:  # noqa: PLR2004
        return f"{phone[:5]} {phone[5:]}"
    return phone
