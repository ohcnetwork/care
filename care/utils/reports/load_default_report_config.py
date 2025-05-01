import json
from pathlib import Path

from django.conf import settings
from pydantic import ValidationError


def load_default_discharge_summary_config(facility=None):
    """Load the default configuration for the discharge summary report from a JSON file.
    If a facility is provided, the configuration will be adjusted accordingly."""
    config_path = (
        Path(settings.BASE_DIR) / "data" / "reports" / "discharge_summary_config.json"
    )
    with config_path.open(encoding="utf-8") as fp:
        data = json.load(fp)

    if facility and "header" in data:
        for row in data["header"].get("rows", []):
            for item in row:
                if (
                    item.get("type") == "text"
                    and item.get("text") == "Central Diagnostic Laboratory"
                ):
                    item["text"] = facility.name

    try:
        from care.emr.resources.template.spec import (
            FacilityReportTemplateCreateSpec,  # circular import
        )

        validated_config = FacilityReportTemplateCreateSpec.model_validate(data)
    except ValidationError as e:
        error = f"Invalid discharge summary config: {e}"
        raise ValueError(error) from e

    return validated_config
