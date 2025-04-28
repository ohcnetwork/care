from django.template.loader import render_to_string

from care.emr.registries.report.renderer import RendererRegistry
from care.emr.reports.renderer.base import Renderer


class TypstRenderer(Renderer):
    """
    Renderer implementation that uses Typst templates.
    """

    def render_list(self, title, rows) -> str:
        """
        Use the Typst list template.
        """
        return render_to_string(
            "reports/typst/list.typ",
            {
                "title": title,
                "rows": rows,
            },
        )

    def render_table(
        self,
        title,
        columns,
        rows,
    ) -> str:
        """
        Use the Typst table template.
        """
        return render_to_string(
            "reports/typst/table.typ",
            {"title": title, "columns": columns, "rows": rows},
        )

    def render_text(self, title: str, text: str) -> str:
        """
        Use the Typst text template.
        """
        return render_to_string(
            "reports/typst/text.typ",
            {
                "title": title,
                "text": text,
            },
        )

    def render_page_layout(self, layout_config: dict) -> str:
        """
        Use the Typst page layout template.
        """
        return render_to_string(
            "reports/typst/page_layout.typ",
            {"layout": layout_config},
        )


RendererRegistry.register("typst", TypstRenderer)
