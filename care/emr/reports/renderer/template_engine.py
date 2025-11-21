from datetime import date, datetime

from jinja2 import (
    BaseLoader,
    Environment,
    StrictUndefined,
    TemplateSyntaxError,
    UndefinedError,
)
from jinja2.sandbox import SandboxedEnvironment


class TemplateEngine:
    def __init__(self, use_sandbox: bool = True, strict_undefined: bool = True):
        self.use_sandbox = use_sandbox
        self.strict_undefined = strict_undefined
        self.env = self._setup_jinja_env()

    def _setup_jinja_env(self):
        env = (
            SandboxedEnvironment(
                loader=BaseLoader(),
                undefined=StrictUndefined if self.strict_undefined else None,
                autoescape=True,
            )
            if self.use_sandbox
            else Environment(
                loader=BaseLoader(),
                undefined=StrictUndefined if self.strict_undefined else None,
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
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return value
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
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return value
        if isinstance(value, datetime):
            return value.strftime(format_str)
        return str(value)

    @staticmethod
    def _filter_time(value: str | datetime, format_str: str = "%I:%M %p") -> str:
        if not value:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return value
        if isinstance(value, datetime):
            return value.strftime(format_str)
        return str(value)

    @staticmethod
    def _filter_currency(value: int | float | str, symbol: str = "₹") -> str:
        if value is None or value == "":
            return ""
        try:
            amount = float(value)
        except (ValueError, TypeError):
            return str(value)

        negative = amount < 0
        amount = abs(amount)
        rupees = int(amount)
        paise = int(round((amount - rupees) * 100))

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
    def _current_date(format_str: str = "%d/%m/%Y") -> str:
        return datetime.now().strftime(format_str)  # noqa: DTZ005

    @staticmethod
    def _current_datetime(format_str: str = "%d/%m/%Y %I:%M %p") -> str:
        return datetime.now().strftime(format_str)  # noqa: DTZ005

    @staticmethod
    def _current_time(format_str: str = "%I:%M %p") -> str:
        return datetime.now().strftime(format_str)  # noqa: DTZ005

    def validate_syntax(self, template_string: str) -> tuple[bool, str]:
        try:
            self.env.parse(template_string)
            return True, ""
        except TemplateSyntaxError as e:
            return False, f"Template syntax error at line {e.lineno}: {e.message}"
        except Exception as e:
            return False, f"Template validation error: {e!s}"

    def extract_variables(self, template_string: str) -> set[str]:
        try:
            from jinja2 import nodes

            ast = self.env.parse(template_string)
            variables = set()

            def visit_node(node):
                if isinstance(node, nodes.Name):
                    variables.add(node.name)
                elif isinstance(node, nodes.Getattr):
                    # Handle dotted access like patient.name
                    path_parts = []
                    current = node

                    while isinstance(current, nodes.Getattr):
                        path_parts.insert(0, current.attr)
                        current = current.node

                    if isinstance(current, nodes.Name):
                        path_parts.insert(0, current.name)
                        variables.add(".".join(path_parts))
                elif isinstance(node, nodes.Getitem):
                    # Handle indexed access like medications.0.name
                    if isinstance(node.node, nodes.Name):
                        variables.add(node.node.name)
                    elif isinstance(node.node, nodes.Getattr):
                        visit_node(node.node)

                # Recursively visit child nodes
                for child in node.iter_child_nodes():
                    visit_node(child)

            visit_node(ast)
            return variables
        except Exception:
            return set()

    def render(self, template_string: str, context: dict) -> str:
        try:
            template = self.env.from_string(template_string)
            return template.render(**context)
        except TemplateSyntaxError as e:
            msg = f"Template syntax error at line {e.lineno}: {e.message}"
            raise TemplateSyntaxError(msg, e.lineno) from e
        except UndefinedError as e:
            msg = f"Undefined variable in template: {e!s}"
            raise UndefinedError(msg) from e
        except Exception as e:
            msg = f"Template rendering error: {e!s}"
            raise Exception(msg) from e
