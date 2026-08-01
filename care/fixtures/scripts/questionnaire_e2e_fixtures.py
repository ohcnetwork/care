"""
Questionnaire E2E fixtures.

Seeds a deterministic set of questionnaires (plus one patient with fresh
encounters) so the frontend can exercise the entire questionnaire feature
in E2E tests. Everything created here is prefixed with ``e2e-`` and uses
deterministic slugs / question ids, so runs are stable across machines.

Run it with::

    python manage.py load_fixtures --path care/fixtures/scripts/questionnaire_e2e_fixtures.py

Requirements: the default fixtures must already be loaded (the script
resolves "FACILITY WITH PATIENTS", the "General Medicine" facility
organization and the default users by name via the API).

Idempotency: the script is additive and safe to run repeatedly against a
populated development database. Before each create it resolves the record
via the API (questionnaires by slug, the patient by phone number,
encounters by patient + status) and skips anything that already exists.
A second run is a no-op, with two deliberate exceptions:

- ``e2e-versioned`` is topped up with follow-up PUTs until it reaches
  ``internal_revision`` 3 (two archived revisions).
- The E2E encounters are re-created when the existing ones are older than
  ~60 days, because the frontend's encounter setup only looks at a 90 day
  ``created_date`` window.

What it seeds:

- ``e2e-kitchen-sink-instance`` / ``e2e-kitchen-sink-facility`` — every
  simple question type, choice + quantity with custom options, groups with
  ``containerClasses`` layout presets, enable_when coverage (boolean
  Yes/No, numeric greater/less, string equals, 2-condition "any"
  behavior, a protected ``disabled_display``), repeating questions and a
  LOINC-bound observation question.
- ``e2e-units`` — unit-semantics coverage: integer/decimal questions with
  a question-level ``unit`` and a quantity question whose
  ``answer_value_set`` is the ``e2e-dose-units`` instance valueset (three
  enumerated UCUM units: mg/g/kg — small enough to render as inline unit
  chips in the frontend).
- ``e2e-subject-location`` / ``e2e-subject-device`` /
  ``e2e-subject-facility`` — minimal facility questionnaires covering the
  remaining subject types.
- ``e2e-org-scope`` — scoped to the "General Medicine" facility
  organization.
- ``e2e-user-scope`` — a user-scoped questionnaire created as
  ``care-fac-admin`` through a second API client. (``care-doctor`` cannot
  be used: the Doctor role does not carry ``can_write_questionnaire``.)
- ``e2e-versioned`` — instance questionnaire with two archived revisions
  (``internal_revision`` 3).
- ``e2e-pagination-001`` … ``e2e-pagination-018`` — tiny active facility
  questionnaires to page past the default page size of 14.
- One patient (phone ``+919999888777``) with one ``planned`` and one
  ``in_progress`` encounter in "FACILITY WITH PATIENTS" / "General
  Medicine", mirroring the default fixture wiring.
"""

import uuid
from datetime import UTC, datetime, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from care.emr.resources.encounter.constants import (
    ClassChoices,
    EncounterPriorityChoices,
)
from care.emr.resources.encounter.constants import (
    StatusChoices as EncounterStatusChoices,
)
from care.emr.models.valueset import ValueSet
from care.fixtures.base import CareFixtureBase, FixtureError
from care.fixtures.context import care_fixture_context

FACILITY_NAME = "FACILITY WITH PATIENTS"
FACILITY_ORG_NAME = "General Medicine"
ADMIN_FACILITY_ORG_NAME = "Administration"
GEO_ORG_NAME = "Kerala"
USER_SCOPE_USERNAME = "care-fac-admin"

E2E_PATIENT_NAME = "E2E QUESTIONNAIRE PATIENT"
E2E_PATIENT_PHONE = "+919999888777"
ENCOUNTER_FRESHNESS_DAYS = 60

PAGINATION_QUESTIONNAIRE_COUNT = 18
VERSIONED_TARGET_REVISION = 3

UCUM_MG = {
    "system": "http://unitsofmeasure.org",
    "code": "mg",
    "display": "milligram",
}
UCUM_G = {
    "system": "http://unitsofmeasure.org",
    "code": "g",
    "display": "gram",
}
UCUM_KG = {
    "system": "http://unitsofmeasure.org",
    "code": "kg",
    "display": "kilogram",
}
UCUM_PER_MIN = {
    "system": "http://unitsofmeasure.org",
    "code": "/min",
    "display": "per minute",
}
UCUM_CEL = {
    "system": "http://unitsofmeasure.org",
    "code": "Cel",
    "display": "degree Celsius",
}

UNITS_VALUESET_SLUG = "e2e-dose-units"
UNITS_QUESTIONNAIRE_SLUG = "e2e-units"
LOINC_HEART_RATE = {
    "system": "http://loinc.org",
    "code": "8867-4",
    "display": "Heart rate",
}


def log(message):
    print(message)  # noqa: T201


def question_id(slug, link_id):
    """Deterministic question id so re-seeded data stays stable."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"care:e2e:{slug}:{link_id}"))


def simple_question(slug, link_id, question_type, text, **kwargs):
    return {
        "id": question_id(slug, link_id),
        "link_id": link_id,
        "type": question_type,
        "text": text,
        **kwargs,
    }


def kitchen_sink_questions(slug):
    """Every simple question type + groups, enable_when, repeats, observation."""
    q = lambda *args, **kwargs: simple_question(slug, *args, **kwargs)  # noqa: E731
    return [
        q("q-string", "string", "Primary symptom"),
        q("q-text", "text", "Detailed history"),
        q("q-url", "url", "Reference document URL"),
        q("q-decimal", "decimal", "Body temperature (C)"),
        q("q-integer", "integer", "Pain score (0-10)"),
        q("q-date", "date", "Symptom onset date"),
        q("q-datetime", "dateTime", "Admission timestamp"),
        q("q-time", "time", "Last medication time"),
        q("q-boolean", "boolean", "Is the patient stable?"),
        q(
            "q-choice",
            "choice",
            "Severity assessment",
            answer_option=[
                {"value": "Mild"},
                {"value": "Moderate", "initial_selected": True},
                {"value": "Severe"},
            ],
        ),
        q(
            "q-quantity",
            "quantity",
            "Dose administered",
            answer_option=[
                {"value": "250"},
                {"value": "500"},
                {"value": "1000"},
            ],
            unit=UCUM_MG,
        ),
        q(
            "grp-main",
            "group",
            "Examination findings",
            styling_metadata={"containerClasses": "grid grid-cols-2"},
            questions=[
                q("q-grp-string", "string", "General appearance"),
                q(
                    "grp-nested",
                    "group",
                    "Cardiovascular",
                    styling_metadata={"containerClasses": "grid grid-cols-1"},
                    questions=[
                        q("q-nested-string", "string", "Heart sounds"),
                    ],
                ),
            ],
        ),
        q(
            "q-ew-yes",
            "string",
            "Stability notes",
            enable_when=[
                {"question": "q-boolean", "operator": "equals", "answer": "Yes"}
            ],
        ),
        q(
            "q-ew-no",
            "text",
            "Escalation plan",
            enable_when=[
                {"question": "q-boolean", "operator": "equals", "answer": "No"}
            ],
        ),
        q(
            "q-ew-greater",
            "string",
            "Severe pain follow-up",
            enable_when=[
                {"question": "q-integer", "operator": "greater", "answer": 7}
            ],
        ),
        q(
            "q-ew-less",
            "string",
            "Low pain follow-up",
            enable_when=[{"question": "q-integer", "operator": "less", "answer": 3}],
        ),
        q(
            "q-ew-equals",
            "string",
            "Fever details",
            enable_when=[
                {"question": "q-string", "operator": "equals", "answer": "fever"}
            ],
        ),
        q(
            "q-ew-any",
            "string",
            "Any-behavior follow-up",
            enable_behavior="any",
            enable_when=[
                {"question": "q-boolean", "operator": "equals", "answer": "Yes"},
                {"question": "q-integer", "operator": "greater", "answer": 5},
            ],
        ),
        q(
            "q-ew-protected",
            "string",
            "Protected note (visible but locked when disabled)",
            disabled_display="protected",
            enable_when=[
                {"question": "q-boolean", "operator": "equals", "answer": "Yes"}
            ],
        ),
        q(
            "q-repeat-choice",
            "choice",
            "Symptoms observed (repeats)",
            repeats=True,
            answer_option=[
                {"value": "Cough"},
                {"value": "Fever"},
                {"value": "Fatigue"},
            ],
        ),
        q("q-repeat-string", "string", "Medications taken (repeats)", repeats=True),
        q(
            "q-obs-heart-rate",
            "integer",
            "Heart rate (bpm)",
            code=LOINC_HEART_RATE,
            is_observation=True,
        ),
    ]


def units_questions(slug):
    """Unit-semantics coverage: integer/decimal with a question-level unit
    (label display) and a quantity whose ``answer_value_set`` is a small,
    bounded unit valueset (renders as inline unit chips in the frontend)."""
    q = lambda *args, **kwargs: simple_question(slug, *args, **kwargs)  # noqa: E731
    return [
        q("q-int-unit", "integer", "Resting heart rate", unit=UCUM_PER_MIN),
        q("q-dec-unit", "decimal", "Body temperature", unit=UCUM_CEL),
        q(
            "q-qty-vs",
            "quantity",
            "Dose given",
            answer_value_set={"slug": UNITS_VALUESET_SLUG},
            unit=UCUM_MG,
        ),
    ]


def questionnaire_definition(slug, title, questions, subject_type="encounter"):
    return {
        "slug": slug,
        "version": "1.0",
        "title": title,
        "description": f"E2E fixture questionnaire ({slug})",
        "status": "active",
        "subject_type": subject_type,
        "styling_metadata": {},
        "questions": questions,
    }


class QuestionnaireE2EFixtures(CareFixtureBase):
    def list_all(self, url, params=None):
        """Fetch every page of a paginated list endpoint."""
        params = {**(params or {}), "limit": 200, "offset": 0}
        results = []
        while True:
            page = self.get(url, params=params)
            page_results = page.get("results", [])
            results.extend(page_results)
            params["offset"] += len(page_results)
            if not page_results or params["offset"] >= page.get("count", 0):
                return results

    def existing_questionnaires_by_slug(self):
        """Head-revision questionnaires keyed by slug (archived rows excluded)."""
        results = self.list_all(reverse("questionnaire-list"))
        return {entry["slug"]: entry for entry in results}

    def find_facility(self, name):
        for facility in self.list_all(reverse("facility-list"), {"name": name}):
            if facility["name"] == name:
                return facility
        msg = f"Facility {name!r} not found — run the default fixtures first"
        raise FixtureError(msg)

    def find_facility_organization(self, facility_id, name):
        url = reverse(
            "facility-organization-list",
            kwargs={"facility_external_id": facility_id},
        )
        for org in self.list_all(url):
            if org["name"] == name:
                return org
        msg = (
            f"Facility organization {name!r} not found — "
            "run the default fixtures first"
        )
        raise FixtureError(msg)

    def find_geo_organization(self, name):
        params = {"name": name, "org_type": "govt"}
        for org in self.list_all(reverse("organization-list"), params):
            if org["name"] == name:
                return org
        msg = f"Organization {name!r} not found — run the default fixtures first"
        raise FixtureError(msg)

    def find_patient_by_phone(self, phone_number):
        results = self.list_all(
            reverse("patient-list"), {"phone_number": phone_number}
        )
        return results[0] if results else None

    def find_encounters(self, patient_id):
        return self.list_all(reverse("encounter-list"), {"patient": patient_id})

    def ensure_facility_org_membership(self, facility, organization, username, role):
        """Add the user to the facility organization when not already a member."""
        url = reverse(
            "facility-organization-users-list",
            kwargs={
                "facility_external_id": facility["id"],
                "facility_organizations_external_id": organization["id"],
            },
        )
        user = self.get_user(username)
        for membership in self.list_all(url):
            if membership.get("user", {}).get("username") == username:
                return
        self.post(url, {"user": user["id"], "role": role["id"]})
        log(f"  membership: added {username} to {organization['name']}")

    def set_facility_organizations(self, questionnaire_id, organization_ids):
        url = reverse(
            "questionnaire-set-facility-organizations",
            kwargs={"external_id": questionnaire_id},
        )
        return self.post(url, {"facility_organizations": organization_ids})

    def update_questionnaire(self, questionnaire_id, data):
        url = reverse(
            "questionnaire-detail", kwargs={"external_id": questionnaire_id}
        )
        return self.put(url, data)


def seed_units_valueset(base):
    """Instance valueset with three enumerated UCUM dose units (mg/g/kg).

    Referenced by slug from the ``e2e-units`` quantity question, so it must
    exist before the questionnaires are created (the questionnaire spec
    validates slug references against instance valuesets). The fixture
    client is a superuser, which instance-valueset creation requires.
    """
    if ValueSet.objects.filter(
        slug=UNITS_VALUESET_SLUG, auth_context="instance", deleted=False
    ).exists():
        log(f"  valueset {UNITS_VALUESET_SLUG}: exists, skipping")
        return
    base.post(
        reverse("value-set-list"),
        {
            "slug": UNITS_VALUESET_SLUG,
            "name": "E2E Dose Units",
            "description": "E2E fixture: bounded UCUM dose units (mg/g/kg)",
            "status": "active",
            "auth_context": "instance",
            "inherited": False,
            "compose": {
                "include": [
                    {
                        "system": "http://unitsofmeasure.org",
                        "concept": [
                            {"code": code["code"], "display": code["display"]}
                            for code in (UCUM_MG, UCUM_G, UCUM_KG)
                        ],
                    }
                ],
                # Explicit empty exclude: ValueSet.create_composition iterates
                # compose.exclude unguarded, so omitting it breaks $expand.
                "exclude": [],
            },
        },
    )
    log(f"  valueset {UNITS_VALUESET_SLUG}: created")


def seed_questionnaires(base, existing, facility, general_medicine, admin_org, geo_org):
    facility_org_ids = [admin_org["id"], general_medicine["id"]]

    def create(definition, *, auth_context, organizations=None, tag_orgs=False):
        slug = definition["slug"]
        if slug in existing:
            log(f"  {slug}: exists, skipping")
            return existing[slug]
        payload = {**definition, "auth_context": auth_context}
        if auth_context == "facility":
            payload["facility"] = facility["id"]
        elif auth_context == "facility_organization":
            payload["facility_organization"] = general_medicine["id"]
        questionnaire = base.create_questionnaire(organizations or [], payload)
        if tag_orgs and auth_context == "facility":
            base.set_facility_organizations(questionnaire["id"], facility_org_ids)
        log(f"  {slug}: created")
        return questionnaire

    create(
        questionnaire_definition(
            "e2e-kitchen-sink-instance",
            "E2E Kitchen Sink (Instance)",
            kitchen_sink_questions("e2e-kitchen-sink-instance"),
        ),
        auth_context="instance",
        organizations=[geo_org["id"]],
    )
    create(
        questionnaire_definition(
            "e2e-kitchen-sink-facility",
            "E2E Kitchen Sink (Facility)",
            kitchen_sink_questions("e2e-kitchen-sink-facility"),
        ),
        auth_context="facility",
        tag_orgs=True,
    )

    create(
        questionnaire_definition(
            UNITS_QUESTIONNAIRE_SLUG,
            "E2E Units Questionnaire",
            units_questions(UNITS_QUESTIONNAIRE_SLUG),
        ),
        auth_context="facility",
        tag_orgs=True,
    )

    for subject_type in ("location", "device", "facility"):
        slug = f"e2e-subject-{subject_type}"
        create(
            questionnaire_definition(
                slug,
                f"E2E {subject_type.title()} Questionnaire",
                [simple_question(slug, "q-note", "string", "Notes")],
                subject_type=subject_type,
            ),
            auth_context="facility",
            tag_orgs=True,
        )

    create(
        questionnaire_definition(
            "e2e-org-scope",
            "E2E Facility Organization Scoped",
            [
                simple_question(
                    "e2e-org-scope", "q-note", "string", "Department note"
                )
            ],
        ),
        auth_context="facility_organization",
    )

    for index in range(1, PAGINATION_QUESTIONNAIRE_COUNT + 1):
        slug = f"e2e-pagination-{index:03d}"
        create(
            questionnaire_definition(
                slug,
                f"E2E Pagination {index:03d}",
                [simple_question(slug, "q-note", "string", "Note")],
            ),
            auth_context="facility",
        )


def seed_user_scope_questionnaire(base, existing, facility, admin_org):
    """Create the user-scoped questionnaire as care-fac-admin.

    care-doctor cannot be used here: the Doctor role does not have
    can_write_questionnaire, so the API rejects the create. The Facility
    Admin role does, and care-fac-admin is (ensured) a member of the
    facility's Administration organization.
    """
    slug = "e2e-user-scope"
    if slug in existing:
        log(f"  {slug}: exists, skipping")
        return
    roles = base.get_roles()
    base.ensure_facility_org_membership(
        facility, admin_org, USER_SCOPE_USERNAME, roles["Facility Admin"]
    )
    user = get_user_model().objects.get(username=USER_SCOPE_USERNAME)
    client = APIClient()
    client.force_authenticate(user=user)
    user_base = CareFixtureBase(client)
    payload = {
        **questionnaire_definition(
            slug,
            "E2E User Scoped",
            [simple_question(slug, "q-note", "string", "Personal note")],
        ),
        "auth_context": "user",
        "facility": facility["id"],
    }
    user_base.post(reverse("questionnaire-list"), payload)
    log(f"  {slug}: created (as {USER_SCOPE_USERNAME})")


def seed_versioned_questionnaire(base, existing):
    """Instance questionnaire with two archived revisions (internal_revision 3)."""
    slug = "e2e-versioned"
    revision_texts = {
        1: "Observation note (v1)",
        2: "Observation note (v2)",
        3: "Observation note (v3)",
    }

    def definition(revision):
        return questionnaire_definition(
            slug,
            "E2E Versioned Questionnaire",
            [
                simple_question(
                    slug, "q-note", "string", revision_texts[revision]
                )
            ],
        )

    questionnaire = existing.get(slug)
    if questionnaire is None:
        questionnaire = base.create_questionnaire([], {
            **definition(1),
            "auth_context": "instance",
        })
        log(f"  {slug}: created")
    current_revision = questionnaire["internal_revision"]
    if current_revision >= VERSIONED_TARGET_REVISION:
        log(f"  {slug}: already at revision {current_revision}, skipping")
        return
    for revision in range(current_revision + 1, VERSIONED_TARGET_REVISION + 1):
        questionnaire = base.update_questionnaire(
            questionnaire["id"], definition(revision)
        )
        log(f"  {slug}: bumped to revision {questionnaire['internal_revision']}")


def seed_patient_and_encounters(base, facility, general_medicine, geo_org):
    patient = base.find_patient_by_phone(E2E_PATIENT_PHONE)
    if patient is None:
        patient = base.create_patient(
            geo_org["id"],
            name=E2E_PATIENT_NAME,
            phone_number=E2E_PATIENT_PHONE,
        )
        log(f"  patient {E2E_PATIENT_NAME}: created")
    else:
        log(f"  patient {E2E_PATIENT_NAME}: exists, skipping")

    freshness_cutoff = datetime.now(UTC) - timedelta(days=ENCOUNTER_FRESHNESS_DAYS)

    def has_fresh_encounter(encounters, status):
        for encounter in encounters:
            if encounter["status"] != status:
                continue
            created_date = encounter.get("created_date")
            if not created_date:
                return True
            created = datetime.fromisoformat(created_date)
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            if created >= freshness_cutoff:
                return True
        return False

    encounters = base.find_encounters(patient["id"])
    for status in (
        EncounterStatusChoices.planned.value,
        EncounterStatusChoices.in_progress.value,
    ):
        if has_fresh_encounter(encounters, status):
            log(f"  encounter ({status}): fresh one exists, skipping")
            continue
        base.create_encounter(
            patient["id"],
            facility["id"],
            organizations=[general_medicine["id"]],
            status=status,
            encounter_class=ClassChoices.imp.value,
            priority=EncounterPriorityChoices.routine.value,
        )
        log(f"  encounter ({status}): created")


def load_fixtures(base):
    facility = base.find_facility(FACILITY_NAME)
    general_medicine = base.find_facility_organization(
        facility["id"], FACILITY_ORG_NAME
    )
    admin_org = base.find_facility_organization(
        facility["id"], ADMIN_FACILITY_ORG_NAME
    )
    geo_org = base.find_geo_organization(GEO_ORG_NAME)
    existing = base.existing_questionnaires_by_slug()
    log("Resolved facility, organizations and existing questionnaires")

    seed_units_valueset(base)
    log("Loading E2E units valueset completed")

    seed_questionnaires(
        base, existing, facility, general_medicine, admin_org, geo_org
    )
    log("Loading E2E questionnaires completed")

    seed_user_scope_questionnaire(base, existing, facility, admin_org)
    log("Loading E2E user-scoped questionnaire completed")

    seed_versioned_questionnaire(base, existing)
    log("Loading E2E versioned questionnaire completed")

    seed_patient_and_encounters(base, facility, general_medicine, geo_org)
    log("Loading E2E patient and encounters completed")


if __name__ == "__main__":
    with care_fixture_context(base_cls=QuestionnaireE2EFixtures) as base:
        load_fixtures(base)
