# CARE Fixture System

The fixture system provides a consistent, API-driven way to seed development and test data. All data is created through Django REST Framework's `APIClient`, ensuring viewset side-effects (slug generation, auto-created records, validations) are exercised — just like real API calls.

## Architecture

```
care/fixtures/
├── __init__.py        # Package init
├── base.py            # CareFixtureBase — all API helper methods
├── constants.py       # Medical codes, data arrays, builder helpers
├── context.py         # care_fixture_context() — setup/teardown context manager
└── fixtures.md        # This file
```

### base.py — CareFixtureBase

A class that wraps `APIClient` with named methods for every resource type. Each method constructs the request payload, calls the API, and returns an `AttrDict` — a dict subclass that supports both attribute access (`org.id`) and key access (`org["id"]`).

**Core methods:**
- `create_organization()` — Geo, role, or supplier orgs
- `create_facility()` — Facilities linked to a geo org
- `create_facility_organization()` — Departments (teams/depts within a facility)
- `create_location()` — Wards, beds, rooms
- `create_device()` — Medical devices
- `create_user()` — Users with role assignments
- `create_patient()` — Patients with Faker-generated data
- `create_encounter()` — Patient encounters

**Lab methods:**
- `create_specimen_definition()` — Specimen types (blood, urine, etc.)
- `create_observation_definition()` — What gets measured
- `create_charge_item_definition()` — Billing items with price components
- `create_activity_definition()` — Lab test activities linking specimen → observation → charge
- `create_lab_test()` — Compositor that creates a full lab test in one call

**Inventory methods:**
- `create_product_knowledge()` — Product catalog entries
- `create_product()` — Facility-specific products
- `create_delivery_order()` — Stock delivery orders
- `create_supply_delivery()` — Individual supply deliveries
- `create_inventory_item()` — Compositor that creates product_knowledge → charge_item → product

**Managing org methods:**
- `link_managing_org()` — Link a managing org to a role org
- `assign_org_role()` — Assign a user to an org with a role
- `get_role_org_roles()` — Fetch all ROLE_ORG roles
- `get_user()` — Fetch a user by username

**Utility methods:**
- `create_resource_category()` — Categories for grouping resources
- `create_healthcare_service()` — Lab or pharmacy services
- `create_questionnaire()` — Questionnaires
- `load_questionnaires_from_file()` — Bulk load from JSON

---

### constants.py — Data & Medical Codes

All fixture data lives here as plain Python dicts and lists. Builder helpers construct complex nested structures.

#### Medical Code Constants

Standard coding systems used throughout:

```python
# UCUM units
UCUM_ML = {"code": "mL", "system": "http://unitsofmeasure.org", "display": "milliliter"}
UCUM_G_DL = {"code": "g/dL", "system": "http://unitsofmeasure.org", "display": "gram per deciliter"}

# LOINC observation codes
LOINC_FASTING_GLUCOSE = {"code": "1558-6", "system": "http://loinc.org", "display": "Fasting glucose"}

# SNOMED procedure codes
SNOMED_VENIPUNCTURE = {"code": "28520004", "system": "http://snomed.info/sct", "display": "Venipuncture"}

# HL7 specimen types
HL7_BLOOD = {"code": "BLD", "system": "http://terminology.hl7.org/CodeSystem/v2-0487", "display": "Whole blood"}
```

#### Builder Helpers

Functions that construct complex nested structures:

```python
# Price components
build_price_components(600.0, include_defaults=True)
# → [{"amount": 600.0, "monetary_component_type": "base"}, ...default taxes/discounts...]

build_price_components(50.0)
# → [{"amount": 50.0, "monetary_component_type": "base"}]

# Observation ranges
make_range("Normal", low=70, high=99)
# → {"category": "Normal", "range": {"low": 70, "high": 99}}

simple_ranges(70, 99, 100)
# → [normal range, borderline range, high range] with standard categories

# Specimen containers & type_tested
make_container("Red top tube", cap="red", ...)
make_type_tested(specimen_type={...}, container={...}, ...)
```

#### Data Arrays

##### LAB_TESTS

Each entry creates a full lab test (specimen → observation → charge_item_definition → activity_definition):

```python
{
    "specimen": {
        "title": "Fasting Blood Glucose Specimen",
        "type_code": HL7_BLOOD,
        "container": [...],
        "type_tested": [...],
    },
    "observation": {
        "title": "Fasting Blood Glucose",
        "code": LOINC_FASTING_GLUCOSE,
        "category": ObservationCategoryChoices.laboratory.value,
        "permitted_data_type": QuestionType.quantity.value,
        "qualified_ranges": simple_ranges(70, 99, 100),
    },
    "charge_item_definition": {
        "title": "Fasting Blood Glucose Test",
        "price_components": build_price_components(600.0, include_defaults=True),
        "description": "...",
        "purpose": "...",
    },
    "activity": {
        "title": "Fasting Blood Glucose",
        "code": SNOMED_FASTING_GLUCOSE,
        "description": "...",
    },
}
```

##### INVENTORY_ITEMS

Each entry creates: product_knowledge → charge_item_definition → product:

```python
{
    "category": "Medications",
    "product_knowledge": {
        "name": "Amoxicillin",
        "base_unit": UCUM_CAPSULE,
        "definitional": ORAL_TABLET_DEFINITIONAL,
        "storage_guidelines": DEFAULT_STORAGE_GUIDELINES,
    },
    "charge_item_definition": {
        "title": "Amoxicillin 500mg Capsule",
        "price_components": build_price_components(50.0),
    },
    "stock_quantity": 20,
}
```

##### MANAGING_ORG_USERS

Each entry either creates a new user or assigns a role to an existing user:

```python
{"action": "create", "username": "care-role-admin", "role": "Admin"},
{"action": "assign", "username": "admin", "role": "Admin"},
```

---

### context.py — care_fixture_context()

A context manager that handles all setup and teardown:

- Creates/authenticates a superuser via `APIClient.force_authenticate()`
- Wraps everything in `transaction.atomic()` (rollback on failure)
- Patches `PatientCreateLock` to avoid Redis dependency
- Bypasses valueset validation
- Suppresses audit log noise
- Runs `sync_permissions_roles` and `sync_valueset`

---

## Writing Custom Fixture Scripts

You can create standalone scripts that use the fixture system outside of the management command.

### Example: `scripts/seed_custom_data.py`

```python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from care.fixtures.context import care_fixture_context
from care.fixtures.constants import *  # noqa: F403

with care_fixture_context() as base:
    # Create an organization
    org = base.create_organization(name="My Hospital Network")

    # Create a facility
    facility = base.create_facility(org.id, name="City Hospital")

    # Fetch auto-created departments
    existing = base.get_facility_organizations(facility.id)

    # Create a patient
    patient = base.create_patient(org.id)

    # Create an encounter
    encounter = base.create_encounter(patient.id, facility.id)

    # Create a lab test using constants
    lab_category = base.create_resource_category(facility.id, "Tests", "charge_item_definition")
    activity_category = base.create_resource_category(facility.id, "Tests", "activity_definition")
    location = base.create_location(facility.id, name="Lab Room")
    service = base.create_healthcare_service(facility.id, name="Lab")

    base.create_lab_test(
        facility.id,
        LAB_TESTS[0],  # Fasting Blood Glucose
        service_id=service.id,
        location_id=location.id,
        charge_category_slug=lab_category.slug,
        activity_category_slug=activity_category.slug,
    )

    print(f"Created facility: {facility.name} ({facility.id})")
```

### Running the script

```bash
# Via Docker
docker compose exec backend bash -c "python scripts/seed_custom_data.py"

# Via local venv
python scripts/seed_custom_data.py

# Or via manage.py shell
python manage.py shell < scripts/seed_custom_data.py
```

### Tips

- **All changes are atomic** — if any API call fails, everything rolls back.
- **Use `base.get_roles()`** to look up role IDs before creating users with specific roles.
- **Every `create_*` method accepts `**kwargs`** — pass any additional fields the API supports.
- **You can also use constants from `constants.py`** — medical codes, price components, and data arrays are all importable.
