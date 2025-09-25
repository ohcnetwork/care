import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from dateutil.parser import isoparse
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from care.emr.models import Encounter, Patient
from care.emr.models.encounter import EncounterOrganization
from care.emr.models.organization import FacilityOrganization
from care.emr.models.scheduling.booking import TokenBooking
from care.emr.utils.auto_time import disable_auto_time
from care.facility.models import Facility
from care.users.models import User

# ---------------------------------------------------------------------------
# Field configuration
# ---------------------------------------------------------------------------
# Required fields to create/update an Encounter
REQUIRED_FIELDS = ["external_id", "patient", "facility"]
# Optional simple scalar / JSON fields directly present on the Encounter model
OPTIONAL_FIELDS = [
    "status",
    "status_history",  # JSON object
    "encounter_class",
    "encounter_class_history",  # JSON object
    "period",  # JSON object
    "hospitalization",  # JSON object
    "priority",
    "external_identifier",
    "care_team",  # JSON (list/dict) - stored verbatim
    "current_location",  # FK via external_id (FacilityLocation) not yet supported here
    "discharge_summary_advice",
    "tags",  # List[int] - tag ids (advanced usage)
    "appointment",  # TokenBooking external_id
    "organizations",  # List[organization external_id] to associate (FacilityOrganization)
    # Optional user external_ids (UUID) for attribution
    "created_by",
    "updated_by",
]
# Extra meta / control fields not persisted directly (override timestamps)
EXTRA_FIELDS = [
    "created_date",  # ISO8601 datetime
    "modified_date",  # ISO8601 datetime
]
ALL_FIELDS = set(REQUIRED_FIELDS + OPTIONAL_FIELDS + EXTRA_FIELDS)

# NOTE: We intentionally do NOT expose facility_organization_cache (auto-maintained)
# nor attempt to resolve current_location to avoid pulling in additional model deps.


class Command(BaseCommand):
    help = (
        "Import encounters from a JSON array or newline-delimited JSON (JSONL). "
        "Creates or updates Encounter records by external_id."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "source",
            type=str,
            help="Path or URL (http/https) to JSON file (array) or JSONL file.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and show summary without writing to DB",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Fail fast on first invalid row instead of skipping",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Rows per DB transaction batch",
        )

    # ------------------------------------------------------------------
    # Input loading helpers
    # ------------------------------------------------------------------
    def fetch_source(self, source: str) -> tuple[str, bool]:
        parsed = urlparse(source)
        if parsed.scheme in {"http", "https"}:
            resp = requests.get(source, timeout=60)
            if resp.status_code != 200:
                raise CommandError(
                    f"Failed to download {source}: HTTP {resp.status_code}"
                )
            return resp.text, True
        path = Path(source).expanduser()
        if not path.exists():
            raise CommandError(f"File not found: {path}")
        return path.read_text(), False

    def load_json(self, raw_text: str) -> Iterable[dict[str, Any]]:
        raw = raw_text.strip()
        if not raw:
            return []
        if raw[0] == "[":  # JSON array
            data = json.loads(raw)
            if not isinstance(data, list):
                raise CommandError("Top-level JSON must be a list of objects")
            return data
        # JSON lines
        records: list[dict[str, Any]] = []
        for i, line in enumerate(raw.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CommandError(f"Invalid JSON on line {i}: {exc}")
            records.append(obj)
        return records

    # ------------------------------------------------------------------
    # Validation & normalization
    # ------------------------------------------------------------------
    def normalize_record(self, rec: dict[str, Any]) -> dict[str, Any]:
        cleaned = {k: v for k, v in rec.items() if k in ALL_FIELDS}
        missing = [f for f in REQUIRED_FIELDS if not cleaned.get(f)]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        # Provide explicit defaults for fields typically absent in import payloads
        # so that creates always initialize them and (by design) updates will reset
        # them to empty structures if omitted. NOTE: Setting organizations to []
        # will remove existing organization associations for an encounter unless
        # the JSON explicitly supplies them. Remove this default if you prefer
        # to preserve existing organizations on partial updates.
        if "status_history" not in cleaned or cleaned.get("status_history") is None:
            cleaned["status_history"] = {}
        if (
            "encounter_class_history" not in cleaned
            or cleaned.get("encounter_class_history") is None
        ):
            cleaned["encounter_class_history"] = {}
        if "hospitalization" not in cleaned or cleaned.get("hospitalization") is None:
            cleaned["hospitalization"] = {}
        if "organizations" not in cleaned or cleaned.get("organizations") is None:
            cleaned["organizations"] = []

        # Validate organizations list if present
        orgs = cleaned.get("organizations")
        if orgs is not None:
            if not isinstance(orgs, list):
                raise ValueError("'organizations' must be a list of external_ids")
            for i, item in enumerate(orgs, start=1):
                if not isinstance(item, str):
                    raise ValueError(f"organizations[{i}] must be a string external_id")

        # Validate tags if present
        tags = cleaned.get("tags")
        if tags is not None:
            if not isinstance(tags, list) or not all(isinstance(t, int) for t in tags):
                raise ValueError("'tags' must be a list of integers (tag ids)")

        # Parse optional timestamp overrides
        for dt_field in ("created_date", "modified_date"):
            if cleaned.get(dt_field):
                try:
                    dt_val = cleaned[dt_field]
                    if isinstance(dt_val, str):
                        dt_val = isoparse(dt_val)
                    if timezone.is_naive(dt_val):
                        dt_val = timezone.make_aware(dt_val)
                    cleaned[dt_field] = dt_val
                except Exception as exc:
                    raise ValueError(f"Invalid {dt_field}: {exc}") from exc

        # Strip empty created_by / updated_by (treat as unset)
        for user_field in ("created_by", "updated_by"):
            if user_field in cleaned and cleaned[user_field] in (None, ""):
                cleaned.pop(user_field, None)

        return cleaned

    # ------------------------------------------------------------------
    # Foreign key resolution helpers
    # ------------------------------------------------------------------
    def resolve_foreign_keys(self, rec: dict[str, Any]) -> dict[str, Any]:
        # Patient
        patient_ext = rec.pop("patient")
        patient_obj = Patient.objects.filter(external_id=patient_ext).first()
        if not patient_obj:
            raise ValueError(f"Patient '{patient_ext}' not found")
        rec["patient"] = patient_obj

        # Facility
        facility_ext = rec.pop("facility")
        facility_obj = Facility.objects.filter(external_id=facility_ext).first()
        if not facility_obj:
            raise ValueError(f"Facility '{facility_ext}' not found")
        rec["facility"] = facility_obj

        # Appointment (optional)
        if "appointment" in rec and rec["appointment"] is not None:
            appt_ext = rec["appointment"]
            if appt_ext == "":
                rec["appointment"] = None
            else:
                appt_obj = TokenBooking.objects.filter(external_id=appt_ext).first()
                if not appt_obj:
                    raise ValueError(f"Appointment '{appt_ext}' not found")
                rec["appointment"] = appt_obj
        return rec

    # ------------------------------------------------------------------
    # Main handler
    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        enable_auto_time = disable_auto_time(Encounter)
        source = options["source"]
        try:
            raw_text, downloaded = self.fetch_source(source)
            if downloaded:
                msg = f"Downloaded source from {source}"
                if hasattr(self.style, "NOTICE"):
                    self.stdout.write(self.style.NOTICE(msg))
                else:
                    self.stdout.write(self.style.WARNING(msg))
            records = list(self.load_json(raw_text))
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(f"Failed to parse input: {exc}")

        total = len(records)
        if total == 0:
            self.stdout.write(self.style.WARNING("No records found in input"))
            return

        normalized: list[dict[str, Any]] = []
        errors: list[str] = []
        for idx, rec in enumerate(records, start=1):
            try:
                normalized.append(self.normalize_record(rec))
            except Exception as exc:
                msg = f"Row {idx}: {exc}"
                if options["strict"]:
                    raise CommandError(msg)
                errors.append(msg)

        del raw_text
        del records

        if errors:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {len(errors)} invalid rows (use --strict to fail):"
                )
            )
            for e in errors[:10]:
                self.stdout.write("  - " + e)
            if len(errors) > 10:
                self.stdout.write(f"  ... {len(errors) - 10} more")

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry run summary:"))
            self.stdout.write(f"  Input rows: {total}")
            self.stdout.write(f"  Valid rows: {len(normalized)}")
            self.stdout.write(f"  Invalid rows: {len(errors)}")
            return

        batch_size = options["batch_size"]
        created = 0
        updated = 0
        failed = 0

        user_cache: dict[str, int] = dict(User.objects.values_list("external_id", "id"))
        facility_org_cache: dict[str, int] = {}

        batch: list[dict[str, Any]] = []

        def flush(batch: list[dict[str, Any]]):
            nonlocal created, updated, failed
            if not batch:
                return
            with transaction.atomic():
                for rec in batch:
                    try:
                        orgs = rec.pop("organizations", None)
                        created_by_ext = rec.pop("created_by", None)
                        updated_by_ext = rec.pop("updated_by", None)
                        rec.pop("patient")
                        rec.pop("facility")
                        ext_id = rec["external_id"]
                        # We'll not pass external_id inside defaults; reserve it for lookup
                        rec_defaults = {
                            k: v for k, v in rec.items() if k != "external_id"
                        }
                        # rec_defaults = self.resolve_foreign_keys(rec_defaults)

                        # Resolve attribution users if provided
                        if created_by_ext:
                            rec_defaults["created_by_id"] = user_cache[created_by_ext]
                        if updated_by_ext:
                            rec_defaults["updated_by_id"] = user_cache[updated_by_ext]
                        encounter_obj, is_created = Encounter.objects.update_or_create(
                            external_id=ext_id, defaults=rec_defaults
                        )
                        # Manage organizations if provided
                        if orgs is not None:
                            # Map external_ids to FacilityOrganization
                            current_org_ids = set(
                                EncounterOrganization.objects.filter(
                                    encounter=encounter_obj
                                ).values_list("organization__external_id", flat=True)
                            )
                            desired_org_ids = set(orgs)
                            # Add missing
                            for org_ext in desired_org_ids - current_org_ids:
                                if org_ext not in facility_org_cache:
                                    org_obj = FacilityOrganization.objects.filter(
                                        external_id=org_ext,
                                        facility=encounter_obj.facility,
                                    ).first()
                                    if not org_obj:
                                        raise ValueError(
                                            f"FacilityOrganization '{org_ext}' not found for facility"
                                        )
                                    facility_org_cache[org_ext] = org_obj.id
                                EncounterOrganization.objects.create(
                                    encounter=encounter_obj,
                                    organization_id=facility_org_cache[org_ext],
                                )
                            # Remove extras
                            for org_ext in current_org_ids - desired_org_ids:
                                EncounterOrganization.objects.filter(
                                    encounter=encounter_obj,
                                    organization_id=facility_org_cache[org_ext],
                                ).delete()
                            # sync cache (save already triggers, but ensure after deletions)
                            encounter_obj.sync_organization_cache()

                        if is_created:
                            created += 1
                        else:
                            updated += 1
                    except Exception as exc:
                        failed += 1
                        self.stderr.write(
                            self.style.ERROR(
                                f"Failure for external_id={rec.get('external_id')}: {exc}"
                            )
                        )

        last_progress_print = 0

        def print_progress(force: bool = False):
            nonlocal last_progress_print
            processed = created + updated + failed
            if force or processed - last_progress_print >= 100:
                last_progress_print = processed
                pct = (processed / max(1, len(normalized))) * 100
                self.stdout.write(
                    f"Progress: {processed}/{len(normalized)} ({pct:0.1f}%) | Created: {created} Updated: {updated} Failed: {failed}\r",
                    ending="",
                )
                self.stdout.flush()

        for rec in normalized:
            batch.append(rec)
            if len(batch) >= batch_size:
                flush(batch)
                print_progress()
                batch = []
        flush(batch)
        print_progress(force=True)
        self.stdout.write("")  # newline after carriage return line

        self.stdout.write(self.style.SUCCESS("Import complete"))
        self.stdout.write(f"  Total input: {total}")
        self.stdout.write(f"  Created: {created}")
        self.stdout.write(f"  Updated: {updated}")
        self.stdout.write(f"  Failed: {failed}")
        self.stdout.write(f"  Skipped (invalid pre-validation): {len(errors)}")

        enable_auto_time()
