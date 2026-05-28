# CARE Fixture System

The fixture system seeds development and test data through Django REST
Framework's `APIClient`, so all viewset side-effects (slug generation,
auto-created records, validations, audit logs) run exactly as they would
for a real API call.

## Architecture

```
care/fixtures/
├── __init__.py
├── base.py              # CareFixtureBase — API helper class
├── constants.py         # Medical codes, builder helpers, data arrays
├── context.py           # care_fixture_context() — setup/teardown
├── scripts/
│   ├── __init__.py
│   └── default_fixtures.py   # Default seed file (loaded by manage.py)
└── fixtures.md          # This file
```

The system has three layers:

| Layer | What it does                                                                                                                                                                                                                                                         | Stable API? |
| --- |----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------| --- |
| `CareFixtureBase` (in `base.py`) | One Python method per resource — wraps `APIClient`, returns an `AttrDict`.                                                                                                                                                                                           | Yes — write your fixtures against this. |
| `constants.py` | Reusable data: medical code constants (LOINC, SNOMED, UCUM, HL7), builder helpers (`build_price_components`, `simple_ranges`, `make_container`), data arrays (`LAB_TESTS`, `INVENTORY_ITEMS`, `MANAGING_ORG_USERS`, `FACILITY_DEPARTMENTS`, `DEFAULT_AVAILABILITY`). | Yes — import what you need. |
| `care/fixtures/scripts/*.py` | Standalone fixture files. The default is `default_fixtures.py`. You can author your own and load them via `--path`.                                                                                                                                                  | This is *your* code; structure it however you like. |

---

## Running fixtures

The `load_fixtures` management command is a generic file runner. It uses
`runpy.run_path(...)` under the hood, which means it can execute **any
Python file on disk** that opens its own `care_fixture_context()`.

```bash
# Default — runs care/fixtures/scripts/default_fixtures.py
python manage.py load_fixtures

# Or via the Makefile
make load-fixtures

# Run a custom file
python manage.py load_fixtures --path care/fixtures/scripts/his.py
```

The command refuses to run unless `DEBUG=True`.

---

## Authoring a new fixture file

A fixture file is just a normal Python file. The contract is:

1. It opens its own `care_fixture_context()`.
2. Inside the context, it calls `base.create_*` methods (and/or constants/helpers from `constants.py`) to create whatever data it needs.

The simplest possible file:

```python
# care/fixtures/scripts/minimal.py
from care.fixtures.context import care_fixture_context

if __name__ == "__main__":
    with care_fixture_context() as base:
        org = base.create_organization(name="My Hospital Network")
        facility = base.create_facility(org.id, name="City Hospital")
        base.create_patient(org.id)
```

Run it:

```bash
python manage.py load_fixtures --path care/fixtures/scripts/minimal.py
```

> The `if __name__ == "__main__":` guard works because `runpy.run_path`
> executes the file with `__name__ == "__main__"`. You can omit the
> guard and put the `with` block at the top level — both are fine.

### CI-injected fixtures

Because `--path` accepts an absolute path and the file doesn't need to
live inside any Python package, a CI workflow can drop a `.py` file
anywhere and load it:

```yaml
- name: Seed PR-specific fixtures
  run: |
    cp ./ci/seed_for_this_pr.py /tmp/
    python manage.py load_fixtures --path /tmp/seed_for_this_pr.py
```

No changes to the loader, no registration, no manifest.

---

## CareFixtureBase API

A class that wraps `APIClient` with named methods for every resource.
Each method builds the request payload, calls the API, and returns an
`AttrDict` — a dict subclass that supports both attribute access
(`org.id`) and key access (`org["id"]`).

### Core resources

- `create_organization(...)` — geo / role / supplier orgs
- `create_facility(...)` — facility tied to a geo org (auto-creates an `Administration` facility-organization)
- `create_facility_organization(...)` — departments inside a facility
- `create_location(...)` — wards, beds, rooms
- `create_device(...)`
- `create_user(...)` — with role/role-org assignments
- `create_patient(...)` — Faker-generated demographics
- `create_encounter(...)`

### Lab & observation

- `create_specimen_definition(...)`
- `create_observation_definition(...)`
- `create_charge_item_definition(...)`
- `create_activity_definition(...)`
- `create_lab_test(...)` — composite that wires specimen → observation → charge → activity in one call

### Inventory

- `create_product_knowledge(...)`
- `create_product(...)`
- `create_request_order(...)` — purchase or transfer order header (`destination` required, optional `origin` for internal transfers)
- `create_supply_request(...)` — line item against a request order; `item` is a `ProductKnowledge` external id
- `create_delivery_order(...)`
- `create_supply_delivery(...)` — defaults to `status="in_progress"`; pass `supplied_item` for external receipts or `supplied_inventory_item` for internal transfers
- `update_supply_delivery(delivery_id, **kwargs)` — PATCH (used to transition `in_progress → completed`)
- `list_inventory_items(facility_id, location_id, **params)` — fetch the current inventory at a location (used to reference the source `InventoryItem` for transfers)
- `create_facility_product(...)` — composite that wires `product_knowledge → charge_item → product` (returns `(product, product_knowledge)`); accepts optional `product_extras` for batch / expiry / purchase price / pack size

### Scheduling

- `add_user_to_facility_organization(...)` — required before scheduling for a practitioner
- `create_schedule(...)`
- `get_slots_for_day(...)` — generates and returns token slots for a given day
- `create_appointment(...)`
- `create_token_queue(...)`, `create_token_sub_queue(...)`, `create_token_category(...)`

### Managing org

- `link_managing_org(...)`
- `assign_org_role(...)`
- `get_role_org_roles()`
- `get_user(username)`

### Reports

- `create_template(...)` — report template (facility-scoped or global).
- `load_templates_from_file(...)` — bulk-load report templates from a JSON file.

### Utilities

- `create_resource_category(...)` — categories for grouping resources
- `create_healthcare_service(...)` — lab or pharmacy services
- `create_questionnaire(...)`
- `load_questionnaires_from_file(...)` — bulk-load from JSON
- `get_roles()`
- `get_facility_organizations(facility_id)`
- `get(...)/post(...)` - if utility unavailable make one can use these to load data

Every `create_*` method accepts `**kwargs` for any additional fields
the API supports.

---

## constants.py — reusable data

### Medical code constants

```python
UCUM_ML        = {"code": "mL",   "system": "http://unitsofmeasure.org",      "display": "milliliter"}
UCUM_G_DL      = {"code": "g/dL", "system": "http://unitsofmeasure.org",      "display": "gram per deciliter"}
LOINC_FASTING_GLUCOSE = {"code": "1558-6",   "system": "http://loinc.org",                                       "display": "Fasting glucose"}
SNOMED_VENIPUNCTURE   = {"code": "28520004", "system": "http://snomed.info/sct",                                 "display": "Venipuncture"}
HL7_BLOOD             = {"code": "BLD",      "system": "http://terminology.hl7.org/CodeSystem/v2-0487",         "display": "Whole blood"}
```

### Builder helpers

```python
build_price_components(600.0, include_defaults=True)
# → [{"amount": 600.0, "monetary_component_type": "base"}, ...default tax/discount entries...]

make_range("Normal", low=70, high=99)
simple_ranges(70, 99, 100)        # → normal / borderline / high
make_container(name="Red top tube", cap="red", ...)
make_type_tested(specimen_type=..., container=..., ...)
```

### Data arrays

- `LAB_TESTS` — each entry creates a full lab test (specimen → observation → charge → activity) via `base.create_lab_test`.
- `INVENTORY_ITEMS` — each entry creates `product_knowledge → charge_item → product` via `base.create_facility_product`. May include a `product_extras` dict (`batch`, `expiration_date`, `purchase_price`, `standard_pack_size`) forwarded to the Product API.
- `MANAGING_ORG_USERS` — `{"action": "create"|"assign", "username": ..., "role": ...}` entries.
- `FACILITY_DEPARTMENTS` — list of department names seeded inside the default facility (20 medical specialties).
- `DEFAULT_AVAILABILITY` — week-long availability (Mon–Sun 09:30–18:30, 18-min slots, 3 tokens/slot) for `create_schedule`.

---

## Bundled report templates

Report templates are seeded from a single JSON file:

```
data/template_fixtures.json
```

Each entry contains the full template body inline as `template_data`,
along with metadata (`name`, `slug_value`, `template_type`, `context`,
`default_format`, `status`, optional `description` / `options`):

```json
[
  {
    "name": "Treatment Summary",
    "slug_value": "treatment-summary",
    "template_type": "encounter_report",
    "context": "encounter_base",
    "default_format": "pdf",
    "status": "active",
    "template_data": "{% set report_title = \"Treatment Summary\" %}\n..."
  }
]
```

`default_fixtures.py` calls `base.load_templates_from_file(facility=facility_id)`
after questionnaires, so every template is scoped to the seeded facility.
Add a new template by appending an entry to the JSON file.

---

## context.py — `care_fixture_context()`

```python
care_fixture_context(base_cls: type[CareFixtureBase] = CareFixtureBase)
```

A context manager that handles all setup and teardown:

- Creates / authenticates a superuser (`admin` / `admin`) via `APIClient.force_authenticate()`.
- Wraps everything in `transaction.atomic()` — if any `create_*` call raises, **everything rolls back**.
- Patches `PatientCreateLock` so patient creation works without Redis.
- Bypasses valueset validation (so fixtures aren't blocked by external code-system lookups).
- Suppresses naive-datetime warnings emitted by internal scheduling code.
- Runs `sync_permissions_roles` and `sync_valueset` before yielding `base`.

Usage is identical inside fixture files and standalone scripts:

```python
from care.fixtures.context import care_fixture_context

with care_fixture_context() as base:
    base.create_organization(name="…")
```

Pass `base_cls=YourSubclass` when you want `base` to be an instance of
a subclass. Can we used for loading fixtures from a plugin:

```python
from care.fixtures.base import CareFixtureBase
from care.fixtures.context import care_fixture_context


class PluginFixture(CareFixtureBase):
    def create_plugin_data(self, facility_id, **kwargs):
        return self.post("/api/v1/plugin-resource/", {"facility": facility_id, **kwargs})


with care_fixture_context(base_cls=PluginFixture) as base:
    base.create_plugin_data(facility_id)
```



---

## Tips

- **Atomic by default** — any failure rolls back the entire run.
- **`base.fake`** is a `Faker` instance for randomized data (`base.fake.company()`, etc.).
- **Use spec enums** (e.g. `OrganizationTypeChoices.govt.value`) instead of hardcoded strings — they survive renames.
- **Need to look up a role ID?** `base.get_roles()` returns a name→role dict.
- **Need to add data after creation?** Just call more `base.create_*` / API methods inside the same `with` block.
