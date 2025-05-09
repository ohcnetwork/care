from care.emr.registries.report.renderer import RendererRegistry
from care.emr.reports.renderer.base import Renderer


class DummyRenderer(Renderer):
    """
    Dummy Renderer implementation.
    """

    def __init__(self):
        super().__init__(name="Dummy")

    def render_list(self, title, rows) -> str:
        pass

    def render_table(
        self,
        title,
        columns,
        rows,
    ) -> str:
        pass

    def render_text(self, title: str, text: str) -> str:
        pass

    def render_page_layout(self, layout_config: dict) -> str:
        pass

    def compile(
        self,
        output_file: str,
        template_code: str,
        included_images: list,
        encounter_external_id: str,
    ):
        pass

    def render_header(self, header_config: dict) -> str:
        pass


RendererRegistry.register("dummy", DummyRenderer)
