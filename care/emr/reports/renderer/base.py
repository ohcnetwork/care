from abc import ABC, abstractmethod


class Renderer(ABC):
    """
    Strategy interface for rendering sections in various formats.
    """

    @abstractmethod
    def render_list(self, title, rows) -> str:
        """
        Render a list-style section.
        :param title: Section title
        :param rows: List of rows, where each row is a sequence of cell values
        :return: Rendered output string
        """
        ...

    @abstractmethod
    def render_table(
        self,
        title,
        columns,
        rows,
    ) -> str:
        """
        Render a table-style section.
        :param title: Section title
        :param columns: List of column header strings
        :param rows: List of rows, each row is a sequence of cell values
        :return: Rendered output string
        """
        ...

    @abstractmethod
    def render_text(self, title: str, text: str) -> str:
        """
        Render a plain text section.
        :param title: Section title
        :param text: Text content
        :return: Rendered output string
        """
        ...

    @abstractmethod
    def render_page_layout(self, layout_config: dict) -> str:
        """
        Render the page layout.
        :param layout_config: Configuration for the page layout
        :return: Rendered output string
        """
        ...
