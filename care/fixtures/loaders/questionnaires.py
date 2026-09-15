from care.fixtures.base import FixtureError
from care.fixtures.loaders.load import load_json

_QUESTIONNAIRE_ROW_META = frozenset({"organization_refs"})


def load_questionnaires(base, organization_ids_by_ref) -> None:
    for entry in load_json("questionnaires"):
        org_ids = [organization_ids_by_ref[ref] for ref in entry["organization_refs"]]
        payload = {
            key: value
            for key, value in entry.items()
            if key not in _QUESTIONNAIRE_ROW_META
        }
        try:
            base.create_questionnaire(org_ids, payload)
        except FixtureError:
            pass
