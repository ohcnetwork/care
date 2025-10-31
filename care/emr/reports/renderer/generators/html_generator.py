from typing import Any

from care.emr.reports.renderer.generators.base import BaseOutputGenerator


class HTMLGenerator(BaseOutputGenerator):
    def generate(self, html: str, options: dict[str, Any] | None = None) -> bytes:
        options = options or {}
        if options.get("wrap_document", False) and "<html" not in html.lower():
            html = self._wrap_html_document(html, options)
        return html.encode("utf-8")

    def _wrap_html_document(self, html_fragment: str, options: dict[str, Any]) -> str:
        title = options.get("title", "Report")
        charset = options.get("charset", "utf-8")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="{charset}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 2em;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }}
        table, th, td {{
            border: 1px solid #ddd;
        }}
        th, td {{
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
    </style>
</head>
<body>
{html_fragment}
</body>
</html>"""

    def get_format(self) -> str:
        return "html"

    def get_supported_options(self) -> dict[str, Any]:
        return {
            "wrap_document": {"type": "boolean", "default": False},
            "title": {"type": "string", "default": "Report"},
            "charset": {"type": "string", "default": "utf-8"},
        }
