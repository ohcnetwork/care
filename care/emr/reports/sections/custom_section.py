from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.sections.base import BaseSection


class CustomSection(BaseSection):
    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)
        self.register_field("text", lambda o: o)
        self.register_field("list", lambda o: o)
        self.register_field("table", lambda o: o)

    def fetch_data(self):
        return None

    def render(self):
        opts = self.opts
        title = opts.get("title", "")
        style = opts.get("style", "text")

        if self.is_table:
            columns = opts.get("columns", [])
            rows = opts.get("rows", [])
            if not columns or not rows:
                return ""
            return self.renderer.render_table(title, columns, rows)

        if style == "list":
            fields = opts.get("fields", [])
            formatted_rows = [
                [
                    [f["label"], f["value"]]
                    for f in field_group
                    if "label" in f and "value" in f
                ]
                for field_group in fields
            ]
            return self.renderer.render_list(title, formatted_rows)

        if style == "text":
            text = opts.get("text", [])
            return self.renderer.render_text(title, text)

        error = f"Unsupported style: {style}"
        raise ValueError(error)


SectionRegistry.register("custom_section", CustomSection)
