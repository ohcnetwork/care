from care.fixtures.base import FixtureError
from care.fixtures.loaders.load import load_json


def load_templates(base, facility_id) -> None:
    for entry in load_json("templates"):
        try:
            base.create_template(facility=facility_id, **entry)
        except FixtureError:
            pass
