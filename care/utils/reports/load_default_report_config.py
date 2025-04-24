import json
from pathlib import Path

from django.conf import settings


def load_default_discharge_summary_config():
    config_path = (
        Path(settings.BASE_DIR) / "data" / "reports" / "discharge_summary_config.json"
    )
    with config_path.open(encoding="utf-8") as fp:
        return json.load(fp)
