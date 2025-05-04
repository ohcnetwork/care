from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.sections.base import BaseSection


class CustomSection(BaseSection):
    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)

    def fetch_data(self):
        return None

    def render(self):
        opts = self.opts
        title = opts.get("title", "")

        if self.is_table:
            columns = opts.get("columns", [])
            rows = opts.get("rows", [])
            return self.renderer.render_table(title, columns, rows)

        style = opts.get("style", "text")
        if style == "list":
            fields = opts.get("fields", [])
            rows = [[f["label"], f["value"]] for f in fields]
            return self.renderer.render_list(title, rows)

        text = opts.get("text", self.DEFAULT_EMPTY)
        return self.renderer.render_text(title, text)


SectionRegistry.register("custom_section", CustomSection)
