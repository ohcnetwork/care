from abc import ABC, abstractmethod


class BaseHeaderBuilder(ABC):
    def __init__(self, gutter: str = "1em"):
        self.grid_rows: list[list[str]] = []
        self.gutter = gutter

    @classmethod
    def from_config(
        cls, header_config: dict, gutter: str = "1em"
    ) -> "BaseHeaderBuilder":
        builder = cls(gutter=gutter)
        for row_cfg in header_config.get("rows", []):
            row_idx = builder.add_row()
            for el in row_cfg:
                builder._add_element(row_idx, el)  # noqa: SLF001
        return builder

    def add_row(self) -> int:
        self.grid_rows.append([])
        return len(self.grid_rows) - 1

    def _add_element(self, row_idx: int, el: dict):
        t = el.get("type")
        align = el.get("align") or "left"

        if t == "text":
            builder_args = {
                "row_idx": row_idx,
                "text": el["text"],
                "size": el["size"],
                "weight": el.get("weight"),
                "align": align,
            }
            self.add_text(**builder_args)

        elif t == "image":
            builder_args = {
                "row_idx": row_idx,
                "file_name": el["file_name"],
                "width": el.get("width"),
                "align": align,
            }
            self.add_image(**builder_args)

        elif t == "rule":
            builder_args = {
                "row_idx": row_idx,
                "length": el.get("length", "100%"),
                "stroke": el.get("stroke", "black"),
                "align": align,
            }
            self.add_rule(**builder_args)

        elif t in ("datetime", "date", "timestamp"):
            builder_args = {
                "row_idx": row_idx,
                "label": el["label"],
                "date_format": el.get("format") or el.get("date_format"),
                "style_fill": el.get("style", {}).get("fill"),
                "style_weight": el.get("style", {}).get("weight"),
                "align": align,
            }
            self.add_datetime(**builder_args)

        else:
            error = f"Unknown element type '{t}'"
            raise ValueError(error)

    @abstractmethod
    def add_text(
        self,
        row_idx: int,
        text: str,
        size: str,
        weight: str | None = None,
        align: str | None = None,
    ): ...

    @abstractmethod
    def add_image(
        self,
        row_idx: int,
        file_name: str,
        width: str | None = None,
        align: str | None = None,
    ): ...

    @abstractmethod
    def add_rule(
        self,
        row_idx: int,
        length: str = "100%",
        stroke: str = "black",
        align: str | None = None,
    ): ...

    @abstractmethod
    def add_datetime(
        self,
        row_idx: int,
        label: str,
        date_format: str,
        style_fill: str | None = None,
        style_weight: str | None = None,
        align: str | None = None,
    ): ...

    @abstractmethod
    def _render_grid_for_row(self, cells: list[str]) -> str: ...

    def render(self) -> str:
        return "\n\n".join(self._render_grid_for_row(r) for r in self.grid_rows)
