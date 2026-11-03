from datetime import date, datetime
from decimal import Decimal

from django.utils.timezone import is_aware, localtime, make_aware
from jinja2 import (
    BaseLoader,
    Environment,
    StrictUndefined,
    TemplateSyntaxError,
    Undefined,
)
from jinja2.sandbox import ImmutableSandboxedEnvironment

from care.emr.reports.context_builder.data_points.base import (
    ContextBuilderBase,
    Field,
    QuerysetContextBuilder,
    template_value,
)
from care.utils.time_util import care_now


class ReportSandbox(ImmutableSandboxedEnvironment):
    """Allow templates to read declared report fields, never builder internals."""

    @staticmethod
    def _is_report_attribute(obj, attribute):
        return (
            isinstance(attribute, str)
            and not attribute.startswith("_")
            and (
                isinstance(getattr(type(obj), attribute, None), Field)
                or (attribute == "filter" and isinstance(obj, QuerysetContextBuilder))
            )
        )

    def getattr(self, obj, attribute):
        # Check before getattr: an undeclared property must not execute either.
        if isinstance(obj, ContextBuilderBase) and not self._is_report_attribute(
            obj, attribute
        ):
            return self.unsafe_undefined(obj, attribute)
        return super().getattr(obj, attribute)

    def getitem(self, obj, argument):
        if isinstance(obj, ContextBuilderBase):
            return self.getattr(obj, argument)
        return super().getitem(obj, argument)

    def is_safe_attribute(self, obj, attr, value):
        if isinstance(obj, ContextBuilderBase) and not self._is_report_attribute(
            obj, attr
        ):
            return False
        return super().is_safe_attribute(obj, attr, value)


class TemplateEngine:
    def __init__(self, use_sandbox: bool = True, strict_undefined: bool = True):
        self.use_sandbox = use_sandbox
        self.strict_undefined = strict_undefined
        self.env = self._setup_jinja_env()

    def _setup_jinja_env(self):
        env = (
            ReportSandbox(
                loader=BaseLoader(),
                undefined=StrictUndefined if self.strict_undefined else Undefined,
                autoescape=True,
            )
            if self.use_sandbox
            else Environment(
                loader=BaseLoader(),
                undefined=StrictUndefined if self.strict_undefined else Undefined,
                autoescape=True,
            )
        )
        env.trim_blocks = True
        env.lstrip_blocks = True

        env.filters["date"] = self._filter_date
        env.filters["datetime"] = self._filter_datetime
        env.filters["time"] = self._filter_time
        env.filters["currency"] = self._filter_currency
        env.filters["phone"] = self._filter_phone

        env.globals["current_date"] = self._current_date
        env.globals["current_datetime"] = self._current_datetime
        env.globals["current_time"] = self._current_time

        return env

    @staticmethod
    def _filter_date(value: str | date | datetime, format_str: str = "%d/%m/%Y") -> str:
        if not value:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except (ValueError, AttributeError):
                return value
        if isinstance(value, datetime):
            if not is_aware(value):
                value = make_aware(value)
            value = localtime(value)
        if isinstance(value, (datetime, date)):
            return value.strftime(format_str)
        return str(value)

    @staticmethod
    def _filter_datetime(
        value: str | datetime, format_str: str = "%d/%m/%Y %I:%M %p"
    ) -> str:
        if not value:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except (ValueError, AttributeError):
                return value
        if isinstance(value, datetime):
            if not is_aware(value):
                value = make_aware(value)
            value = localtime(value)
            return value.strftime(format_str)
        return str(value)

    @staticmethod
    def _filter_time(value: str | datetime, format_str: str = "%I:%M %p") -> str:
        if not value:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except (ValueError, AttributeError):
                return value
        if isinstance(value, datetime):
            if not is_aware(value):
                value = make_aware(value)
            value = localtime(value)
            return value.strftime(format_str)
        return str(value)

    @staticmethod
    def _filter_currency(value: int | float | str, symbol: str = "₹") -> str:
        if value is None or value == "":
            return ""
        try:
            amount = Decimal(value)
        except (ValueError, TypeError):
            return str(value)

        negative = amount < 0
        amount = abs(amount)
        rupees = int(amount)
        paise = round((amount - rupees) * 100)

        rupees_str = str(rupees)
        if len(rupees_str) <= 3:  # noqa: PLR2004
            formatted = rupees_str
        else:
            last_three = rupees_str[-3:]
            remaining = rupees_str[:-3]
            formatted = ""
            for i, digit in enumerate(reversed(remaining)):
                if i > 0 and i % 2 == 0:
                    formatted = "," + formatted
                formatted = digit + formatted
            formatted = formatted + "," + last_three

        if paise > 0:
            formatted = f"{formatted}.{paise:02d}"

        result = f"{symbol}{formatted}"
        if negative:
            result = f"-{result}"
        return result

    @staticmethod
    def _filter_phone(value: str) -> str:
        if not value:
            return ""
        phone = (
            str(value)
            .replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
        )
        if phone.startswith("+91") and len(phone) >= 13:  # noqa: PLR2004
            return f"+91 {phone[3:8]} {phone[8:]}"
        if len(phone) == 10:  # noqa: PLR2004
            return f"{phone[:5]} {phone[5:]}"
        return phone

    @staticmethod
    def _current_date() -> date:
        return TemplateEngine._filter_date(care_now())

    @staticmethod
    def _current_datetime() -> datetime:
        return TemplateEngine._filter_datetime(care_now())

    @staticmethod
    def _current_time() -> str:
        return TemplateEngine._filter_time(care_now())

    def validate_syntax(self, template_string: str) -> tuple[bool, str]:
        try:
            self.env.parse(template_string)
            return True, ""
        except TemplateSyntaxError as e:
            return False, f"Template syntax error at line {e.lineno}: {e.message}"
        except Exception as e:
            return False, f"Template validation error: {e!s}"

    def render(self, template_string: str, context: dict) -> str:
        try:
            template = self.env.from_string(template_string)
            return template.render(**template_value(context))
        except TemplateSyntaxError as e:
            msg = f"Template syntax error at line {e.lineno}: {e.message}"
            raise TemplateSyntaxError(msg, e.lineno) from e
        except Exception as e:
            raise e
