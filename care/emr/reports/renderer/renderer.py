import logging

from care.emr.reports.renderer.generators.base import BaseOptions, BaseOutputGenerator
from care.emr.reports.renderer.template_engine import TemplateEngine

logger = logging.getLogger(__name__)


class Renderer:
    def __init__(
        self,
        output_generator: BaseOutputGenerator,
        template_engine: TemplateEngine | None = None,
    ):
        self.template_engine = template_engine or TemplateEngine()
        self.output_generator = output_generator

    def render(
        self, template_string: str, context: dict, options: BaseOptions | None = None
    ) -> bytes:
        options = options or BaseOptions()

        try:
            html = self.template_engine.render(template_string, context)
        except Exception as e:
            logger.error("Template rendering failed: %s", e)
            msg = "Failed to render template"
            raise Exception(msg) from e

        try:
            return self.output_generator.generate(html, options)
        except Exception as e:
            logger.error("Output generation failed: %s", e)
            msg = f"Failed to generate {self.output_generator.get_format()}"
            raise Exception(msg) from e
