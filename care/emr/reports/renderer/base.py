from abc import ABC, abstractmethod


class Renderer(ABC):
    """
    Strategy interface for rendering sections in various formats.
    """

    def __init__(self, name: str):
        self.name = name

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

    @abstractmethod
    def compile(
        self,
        output_file: str,
        template_code: str,
        included_images: list,
        encounter_external_id: str,
    ):
        """
        Compile the rendered template into a final output format (e.g., PDF).
        :param output_file: Path to the output file
        :param template_code: Rendered template code
        :param included_images: List of images to include in the output
        :param encounter_external_id: Encounter ID for logging or tracking
        """
        ...

    @abstractmethod
    def render_header(self, header_config: dict) -> str:
        """
        Render the header section.
        :param header_config: Configuration for the header
        :return: Rendered output string
        """
        ...
