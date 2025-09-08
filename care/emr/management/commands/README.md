# EMR Management Commands

This directory contains Django management commands for the EMR module.
Run with:

```
python manage.py <command_name> [options]
```

## Available Commands

| Command | Purpose |
|---------|---------|
| `import_patients` | Import or update Patient records from JSON / JSONL by `external_id`. |
| `load_fixtures` | Load predefined EMR data fixtures. |
| `load_govt_organization` | Load government organization hierarchy (JSON). |
| `load_govt_organization_csv` | Load government organization hierarchy (CSV). |
| `migrate_facility_organization` | Migrate legacy facility -> organization links. |
| `sync_valueset` | Synchronize FHIR valuesets / coded concepts. |
| `fix_parent_locations_has_children` | Repair cached parent location flags. |
| `test_emr` | Lightweight internal smoke / dev tests. |

---
## `import_patients`
Import patients from a JSON array file, newline‑delimited JSON (JSONL), or a remote URL (http/https). Creates or updates rows keyed by `external_id`.

### Supported Fields
`external_id` (required) plus optional: `name`, `gender`, `phone_number`, `emergency_phone_number`, `address`, `permanent_address`, `pincode`, `date_of_birth`, `year_of_birth`, `deceased_datetime`, `marital_status`, `blood_group`, `geo_organization` (organization `external_id`).

Structured field:
- `identifiers`: list of objects `{ "config": "<identifier_config_external_id>", "value": "<string or empty>" }`
  - If `value` is null/empty string and an identifier exists, it is deleted.
  - If identifier config refers to a facility-specific config, the facility relation is applied automatically.

### Usage
```
# Local file
python manage.py import_patients patients.json

# Remote URL (download then import)
python manage.py import_patients https://example.com/patients.json

# Dry run (no DB writes)
python manage.py import_patients patients.json --dry-run

# Strict mode + custom batch size
python manage.py import_patients https://example.com/patients.json --strict --batch-size 500
```

### Options
- `--dry-run`  Validate and show a summary without DB writes.
- `--strict`   Stop immediately on first invalid row (default: skip and continue).
- `--batch-size N`  Process records in transactions of N (default 100).

### Input Formats
1. JSON array file:
```json
[
  {
    "external_id": "P001",
    "name": "John Doe",
    "gender": "M",
    "geo_organization": "ORG001",
    "identifiers": [
      {"config": "NATIONAL_ID", "value": "ABC123"},
      {"config": "HOSPITAL_MRN", "value": "MRN-0099"}
    ]
  }
]
```
2. Newline-delimited JSON (JSONL):
```
{"external_id": "P001", "name": "John Doe"}
{"external_id": "P002", "name": "Jane Smith"}
```

### Behavior
- Existing patients matched by `external_id` are updated (idempotent import).
- `geo_organization` resolves by `Organization.external_id`; missing org in strict mode raises error; otherwise row fails and is counted.
- Unknown fields are ignored.
- Shows a dynamic progress line every ~100 processed rows (created/updated/failed) and a final summary.
- Applies / updates / deletes patient identifiers atomically with each patient record.

### Download & Network Notes
- If the source starts with http/https it is fetched via a GET request (60s timeout).
- Non-200 status codes abort the import.
- Currently no retry/backoff; wrap with external retry if needed.

### Exit Codes
- `0` success (even with skipped rows unless `--strict`).
- `1` fatal error (file missing, parse error, strict validation failure).

---
## Conventions
- Add new commands with clear help text (`help` attribute) and document them here.
- Prefer idempotent imports (use natural keys like `external_id`).
- Use `--dry-run` style flag for bulk mutating commands when feasible.

---
## Maintenance
If a command becomes obsolete, mark it deprecated in this README before removal to aid operators.
