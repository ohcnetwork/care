from care.emr.reports.headers.base import BaseHeaderBuilder


class TypstHeaderBuilder(BaseHeaderBuilder):
    def add_text(
        self,
        row_idx: int,
        text: str,
        size: str,
        weight: str | None = None,
        align: str | None = None,
    ):
        parts = [f"size: {size}"]
        if weight:
            parts.append(f"weight: {weight}")
        cfg = ", ".join(parts)
        frag = f"text({cfg})[= {text}]"
        if align:
            frag = f"align({align}, {frag})"
        self.grid_rows[row_idx].append(frag)

    def add_image(
        self,
        row_idx: int,
        file_name: str,
        width: str | None = None,
        align: str | None = None,
    ):
        parts = []
        if width:
            parts.append(f"width: {width}")
        cfg = ", ".join(parts)
        frag = f'image("{file_name}"{", " + cfg if cfg else ""})'
        if align:
            frag = f"align({align}, {frag})"
        self.grid_rows[row_idx].append(frag)

    def add_rule(
        self,
        row_idx: int,
        length: str = "100%",
        stroke: str = "black",
        align: str | None = None,
    ):
        frag = f"line(length: {length}, stroke: {stroke})"
        if align:
            frag = f"align({align}, {frag})"
        self.grid_rows[row_idx].append(frag)

    def add_datetime(
        self,
        row_idx: int,
        label: str,
        date_format: str,
        style_fill: str | None = None,
        style_weight: str | None = None,
        align: str | None = None,
    ):
        parts = []
        if style_fill:
            parts.append(f"fill: {style_fill}")
        if style_weight:
            parts.append(f"weight: {style_weight}")
        cfg = ", ".join(parts)
        frag = f'text({cfg})[*{label}* #datetime.today().display("{date_format}")]'
        if align:
            frag = f"align({align}, {frag})"
        self.grid_rows[row_idx].append(frag)

    def _render_grid_for_row(self, cells: list[str], size_ratio: list[int]) -> str:
        def convert_ratio_to_typst(ratio: list[int]) -> str:
            fr_parts = [f"{x}fr" for x in ratio]
            return f"({', '.join(fr_parts)})"

        columns_typst = convert_ratio_to_typst(size_ratio)
        lines = []
        for i, frag in enumerate(cells):
            comma = "," if i < len(cells) - 1 else ""
            lines.append(f"  [#{frag}]{comma}")
        body = "\n".join(lines)
        return (
            f"#grid(columns: {columns_typst}, column-gutter: {self.gutter}, align: center,\n"
            f"{body}\n)"
        )
