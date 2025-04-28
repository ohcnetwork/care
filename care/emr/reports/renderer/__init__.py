from care.emr.reports.renderer.renderer_registry import RendererRegistry
from care.emr.reports.renderer.typst_renderer import TypstRenderer

RendererRegistry.register("typst", TypstRenderer)
