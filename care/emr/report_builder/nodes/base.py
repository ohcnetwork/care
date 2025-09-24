from enum import Enum

from pydantic import BaseModel


class NodeType(str, Enum):
    functional = "functional"
    display = "display"
    iteration = "iteration"
    conditional = "conditional"


class RenderProperties(BaseModel):
    class_names: list[str] = []


class ReportBaseNode:
    NAME = ""
    TYPE = None
    DESCRIPTION = ""
    CONTEXT_NAME = ""
    REQUIRED_CONTEXTS = []
    ADDITIONAL_CONTEXT = ""
    CAN_HAVE_CHILDREN = True
    FILTER_CLASS = None

    def __init__(
        self,
        properties: dict,
        children: list = None,
        context: dict = None,
        cache: dict = None,
    ):
        self.properties = properties
        if not context:
            context = {}
        self.context = context
        if not children:
            children = []
        self.children = children
        if not cache:
            cache = {}
        self.cache = cache

    def get_iterator(self):
        return []

    def get_html_attributes(self):
        return ""

    def render_children(self):
        html_content = ""
        for child in self.children:
            html_content += child.render_to_html(context=self.context)
        return html_content

    def render_to_html(self, context: dict = None):
        if context:
            self.context = context
        if NodeType.functional.value == self.TYPE:
            return self._render_to_html()
        if NodeType.display.value == self.TYPE:
            return self._render_to_html()
        if NodeType.iteration.value == self.TYPE:
            iterator = self.get_iterator()
            html_content = ""
            for item in iterator:
                self.context[self.CONTEXT_NAME] = item
                html_content += self._render_to_html()
        return ""

    def _render_to_html(self):
        return ""
