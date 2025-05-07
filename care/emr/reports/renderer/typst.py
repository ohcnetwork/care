import logging
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string

from care.emr.registries.report.renderer import RendererRegistry
from care.emr.reports.headers.typst_header import TypstHeaderBuilder
from care.emr.reports.renderer.base import Renderer
from care.emr.reports.utils import download_image_to_cache

logger = logging.getLogger(__name__)


class TypstRenderer(Renderer):
    """
    Renderer implementation that uses Typst templates.
    """

    def __init__(self):
        super().__init__(name="typst")

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

    def compile(
        self,
        output_file: str,
        template_code: str,
        included_images: list,
        encounter_external_id: str,
    ):
        """Compile Typst template into PDF"""
        logger.info("Compiling PDF for %s → %s", encounter_external_id, output_file)
        logger.info("\n" * 20)
        logger.info(template_code)
        logger.info("\n" * 20)
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "template.typ"
            template_path.write_text(template_code)

            for file_name, url in included_images:
                try:
                    image_bytes = download_image_to_cache(file_name, url)
                    image_path = Path(tmpdir) / file_name
                    with image_path.open("wb") as f:
                        f.write(image_bytes)
                except Exception as e:
                    logger.error(
                        "Failed to download or validate image '%s' from '%s' for encounter %s: %s",
                        file_name,
                        url,
                        encounter_external_id,
                        str(e),
                    )
                    error = f"Image '{file_name}' is invalid or corrupted. Aborting compilation for encounter {encounter_external_id}."

                    raise RuntimeError(error) from e

            try:
                subprocess.run(  # noqa: S603
                    [
                        settings.TYPST_BIN,
                        "compile",
                        str(template_path.name),
                        str(output_file),
                    ],
                    cwd=tmpdir,
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                logger.error(
                    "Typst compilation failed for %s: %s",
                    encounter_external_id,
                    e.stderr,
                )
                error = f"Failed to compile PDF for encounter {encounter_external_id}: {e.stderr.strip()}"

                raise RuntimeError(error) from e

        logger.info("Successfully compiled PDF for %s", encounter_external_id)

    def render_header(self, header_config: dict) -> str:
        header_builder = TypstHeaderBuilder.from_config(header_config)
        return header_builder.render()


RendererRegistry.register("typst", TypstRenderer)
