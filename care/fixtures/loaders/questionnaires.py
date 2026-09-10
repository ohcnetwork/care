"""Load pack questionnaire definitions from questionnaires.json.

Get-or-create by slug (globally unique). Attach role orgs via
``organization_refs`` resolved from the pack organization map.
"""

from django.urls import reverse

from care.fixtures.base import log
from care.fixtures.loaders.load import load_json

_QUESTIONNAIRE_ROW_META = frozenset({"organization_refs"})


def load_questionnaires(base, organization_ids_by_ref) -> dict[str, str]:
    """Create or reuse pack questionnaires; return slug → external id."""
    rows = load_json("questionnaires")
    existing_by_slug = _existing_questionnaires_by_slug(base)
    questionnaire_ids_by_slug: dict[str, str] = {}

    for entry in rows:
        org_ids = [organization_ids_by_ref[ref] for ref in entry["organization_refs"]]
        payload = {
            key: value
            for key, value in entry.items()
            if key not in _QUESTIONNAIRE_ROW_META
        }
        slug = payload["slug"]
        existing = existing_by_slug.get(slug)
        if existing is not None:
            questionnaire_ids_by_slug[slug] = str(existing.id)
            log(f"Reused questionnaire {slug!r}")
            continue

        created = base.create_questionnaire(org_ids, payload)
        questionnaire_ids_by_slug[slug] = str(created.id)
        existing_by_slug[slug] = created
        log(f"Created questionnaire {slug!r}")

    log(f"Loaded {len(questionnaire_ids_by_slug)} questionnaires")
    return questionnaire_ids_by_slug


def _existing_questionnaires_by_slug(base) -> dict:
    """List questionnaires once; avoid detail GETs that 404 on first create."""
    data = base.get(reverse("questionnaire-list"), params={"limit": 100})
    results = data.get("results", data)
    return {q.slug: q for q in results}
