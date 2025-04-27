import hashlib
import logging

import requests
from django.core.cache import cache
from django.template.loader import render_to_string

from care.emr.models import (
    AllergyIntolerance,
    Condition,
    FileUpload,
    Observation,
)
from care.emr.models.medication_request import MedicationRequest
from care.emr.reports.base import BaseSection
from care.emr.resources.condition.spec import CategoryChoices
from care.facility.models import User
from care.utils.lock import Lock

logger = logging.getLogger(__name__)


class SymptomSection(BaseSection):
    def __init__(self, config, context):
        super().__init__(config, context)
        self.field_extractors.update(
            {
                "symptom": lambda o: o.code.get("display")
                if o.code
                else self.DEFAULT_EMPTY,
                "onset": lambda o: o.onset.get("onset_datetime")
                if o.onset
                else self.DEFAULT_EMPTY,
            }
        )

    def fetch_data(self):
        return Condition.objects.filter(
            encounter=self.context["encounter"],
            category=CategoryChoices.problem_list_item,
        )


class DiagnosisSection(BaseSection):
    def __init__(self, config, context):
        super().__init__(config, context)
        self.field_extractors.update(
            {
                "diagnosis": lambda o: o.code.get("display")
                if o.code
                else self.DEFAULT_EMPTY,
                "onset": lambda o: o.onset.get("onset_datetime")
                if o.onset
                else self.DEFAULT_EMPTY,
            }
        )

    def fetch_data(self):
        return Condition.objects.filter(
            encounter=self.context["encounter"],
            category=CategoryChoices.encounter_diagnosis,
        )


class AllergySection(BaseSection):
    def __init__(self, config, context):
        super().__init__(config, context)
        self.field_extractors.update(
            {
                "allergen": lambda o: o.code.get("display")
                if o.code
                else self.DEFAULT_EMPTY,
                "onset": lambda o: o.onset.get("onset_datetime")
                if o.onset
                else self.DEFAULT_EMPTY,
            }
        )

    def fetch_data(self):
        return AllergyIntolerance.objects.filter(encounter=self.context["encounter"])


def _get_observation_value(o: Observation):
    if disp := o.value.get("display"):
        return disp
    if unit := o.value.get("unit", {}).get("display"):
        v = o.value.get("value")
        if isinstance(v, (int, float)) and getattr(v, "is_integer", lambda: False)():
            v = int(v)
        return f"{v} {unit}" if unit else v
    return o.value.get("value", BaseSection.DEFAULT_EMPTY)


class ObservationSection(BaseSection):
    def __init__(self, config, context):
        super().__init__(config, context)
        self.field_extractors.update(
            {
                "observation": lambda o: o.main_code.get("display")
                if o.main_code
                else self.DEFAULT_EMPTY,
                "value": _get_observation_value,
                "date": lambda o: o.effective_datetime
                or o.created_date
                or self.DEFAULT_EMPTY,
            }
        )

    def fetch_data(self):
        return Observation.objects.filter(encounter=self.context["encounter"])


def _med_dosage(o: MedicationRequest):
    try:
        return o.dosage_instruction[0]["text"] or BaseSection.DEFAULT_EMPTY
    except Exception:
        return BaseSection.DEFAULT_EMPTY


class MedicationRequestSection(BaseSection):
    def __init__(self, config, context):
        super().__init__(config, context)
        self.field_extractors.update(
            {
                "medication": lambda m: m.medication.get("display", self.DEFAULT_EMPTY),
                "value": _med_dosage,
                "date": lambda m: m.authored_on or m.created_date or self.DEFAULT_EMPTY,
            }
        )

    def fetch_data(self):
        return MedicationRequest.objects.filter(encounter=self.context["encounter"])


class PatientInfoSection(BaseSection):
    def fetch_data(self):
        return [self.context["encounter"].patient]


class CareTeamSection(BaseSection):
    def __init__(self, config, context):
        super().__init__(config, context)
        self.field_extractors.update(
            {
                "name": lambda u: u.full_name,
                "role": self._get_role_for,
            }
        )

    @property
    def _role_map(self):
        return {
            m["user_id"]: m["role"]["display"]
            for m in self.context["encounter"].care_team
            if m.get("user_id") and m.get("role")
        }

    def _get_role_for(self, user: User):
        return self._role_map.get(user.id, "Unknown")

    def fetch_data(self):
        ids = [m["user_id"] for m in self.context["encounter"].care_team]
        return User.objects.filter(id__in=ids)


class FileSection(BaseSection):
    def fetch_data(self):
        return FileUpload.objects.filter(
            associating_id=self.context["encounter"].external_id,
            upload_completed=True,
            is_archived=False,
        )


class DischargeAdviceSection(BaseSection):
    def fetch_data(self):
        return [self.context["encounter"].discharge_summary_advice or ""]


class CustomTextSection(BaseSection):
    def fetch_data(self):
        # Custom sections don't fetch from DB
        return None

    def render(self):
        opts = self.opts
        title = opts.get("title", "")

        if self.is_table:
            columns = opts.get("columns", [])
            rows = opts.get("rows", [])
            return render_to_string(
                "reports/typst/table.typ",
                {"title": title, "columns": columns, "rows": rows},
            )

        style = opts.get("style", "text")
        if style == "list":
            fields = opts.get("fields", [])
            rows = [[f["label"], f["value"]] for f in fields]
            return render_to_string(
                "reports/typst/list.typ", {"title": title, "rows": rows}
            )

        # Default to plain text
        text = opts.get("text", "")
        return render_to_string(
            "reports/typst/text.typ", {"title": title, "text": text}
        )


class HeaderBuilder:
    def __init__(self, gutter: str = "1em"):
        self.grid_rows: list[list[str]] = []
        self.gutter = gutter

    @classmethod
    def from_config(cls, header_config: dict, gutter: str = "1em") -> "HeaderBuilder":
        builder = cls(gutter=gutter)
        for row_cfg in header_config.get("rows", []):
            row_idx = builder.add_row()
            for el in row_cfg:
                t = el["type"]
                align = el.get("align") or "left"
                if t == "text":
                    builder.add_text(
                        row_idx,
                        text=el["text"],
                        size=el["size"],
                        weight=el.get("weight"),
                        align=align,
                    )
                elif t == "image":
                    builder.add_image(
                        row_idx,
                        file_name=el["file_name"],
                        width=el.get("width"),
                        align=align,
                    )
                elif t == "rule":
                    builder.add_rule(
                        row_idx,
                        length=el.get("length", "100%"),
                        stroke=el.get("stroke", "black"),
                        align=align,
                    )
                elif t in ("datetime", "date", "timestamp"):
                    builder.add_datetime(
                        row_idx,
                        label=el["label"],
                        date_format=el.get("format") or el.get("date_format"),
                        style_fill=el.get("style", {}).get("fill"),
                        style_weight=el.get("style", {}).get("weight"),
                        align=align,
                    )
                else:
                    error = f"Unknown header element type: {t!r}"
                    logging.error(error)
        return builder

    def add_row(self) -> int:
        self.grid_rows.append([])
        return len(self.grid_rows) - 1

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

    def _render_grid_for_row(self, cells: list[str]) -> str:
        count = len(cells)
        lines = []
        for i, frag in enumerate(cells):
            comma = "," if i < count - 1 else ""
            lines.append(f"  [#{frag}]{comma}")
        body = "\n".join(lines)
        return (
            f"#grid(columns: {count}, column-gutter: {self.gutter}, align: center,\n"
            f"{body}\n"
            ")"
        )

    def render(self) -> str:
        return "\n\n".join(self._render_grid_for_row(r) for r in self.grid_rows)


def download_image_to_cache(file_name, url):
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    cache_key = f"image_cache:{file_name}:{url_hash}"

    cached_image = cache.get(cache_key)

    if cached_image:
        return cached_image

    with Lock(cache_key):
        cached_image = cache.get(cache_key)
        if cached_image:
            return cached_image

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        cache.set(cache_key, response.content, timeout=24 * 60 * 60)
        return response.content
