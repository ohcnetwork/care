import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from care.emr.models import (
    Organization,
    Patient,
    PatientIdentifier,
    PatientIdentifierConfig,
)

REQUIRED_FIELDS = ["external_id"]
OPTIONAL_FIELDS = [
    "name",
    "gender",
    "phone_number",
    "emergency_phone_number",
    "address",
    "permanent_address",
    "pincode",
    "date_of_birth",
    "year_of_birth",
    "deceased_datetime",
    "marital_status",
    "blood_group",
    "geo_organization",
]
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

# Additional structured fields (not in model directly)
STRUCTURED_FIELDS = {"identifiers"}

# Constants for magic numbers / values
HTTP_OK = 200
SAMPLE_ERROR_DISPLAY_LIMIT = 10
PROGRESS_INTERVAL = 100


class Command(BaseCommand):
    help = "Import patients from a JSON file (array or newline-delimited). Creates or updates by external_id."

    def add_arguments(self, parser):
        parser.add_argument(
            "source",
            type=str,
            help="Path or URL to the JSON file (list or JSONL). If URL (http/https), it will be downloaded.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and show summary without writing to DB",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Fail fast on first error instead of skipping",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of rows per DB transaction batch",
        )

    def fetch_source(self, source: str) -> tuple[str, bool]:
        """Return the raw text content of a local path or URL.

        Returns (text, downloaded) where downloaded indicates a network fetch.
        """
        parsed = urlparse(source)
        if parsed.scheme in {"http", "https"}:
            resp = requests.get(source, timeout=60)
            if resp.status_code != HTTP_OK:
                msg = f"Failed to download {source}: HTTP {resp.status_code}"
                raise CommandError(msg)
            return resp.text, True
        # treat as file path
        path = Path(source).expanduser()
        if not path.exists():
            msg = f"File not found: {path}"
            raise CommandError(msg)
        return path.read_text(), False

    def load_json(self, raw_text: str) -> Iterable[dict[str, Any]]:
        """Support two formats: a single JSON array OR newline delimited JSON (JSONL)."""
        raw = raw_text.strip()
        if not raw:
            return []
        if raw[0] == "[":  # JSON array
            data = json.loads(raw)
            if not isinstance(data, list):
                raise CommandError("Top-level JSON must be a list of objects")
            return data
        # Assume JSONL
        records: list[dict[str, Any]] = []
        for i, raw_line in enumerate(raw.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                msg = f"Invalid JSON on line {i}: {exc}"
                raise CommandError(msg) from exc
            records.append(obj)
        return records

    def normalize_record(self, rec: dict[str, Any]) -> dict[str, Any]:
        # Only keep known direct model fields + structured
        cleaned = {
            k: v for k, v in rec.items() if k in ALL_FIELDS or k in STRUCTURED_FIELDS
        }
        missing = [f for f in REQUIRED_FIELDS if not cleaned.get(f)]
        if missing:
            msg = "Missing required fields: {}".format(", ".join(missing))
            raise ValueError(msg)
        # Basic validation for identifiers
        identifiers = cleaned.get("identifiers")
        if identifiers is not None:
            if not isinstance(identifiers, list):
                raise ValueError(
                    "'identifiers' must be a list of {config: <external_id>, value: <str>}"
                )
            norm_identifiers = []
            for i, item in enumerate(identifiers, start=1):
                if not isinstance(item, dict):
                    msg = f"identifiers[{i}] must be an object"
                    raise ValueError(msg)
                cfg = item.get("config")
                val = item.get("value")
                if not cfg:
                    msg = f"identifiers[{i}].config is required"
                    raise ValueError(msg)
                if val in (None, ""):
                    # skip empty value (treated as delete if exists)
                    norm_identifiers.append({"config": cfg, "value": None})
                else:
                    norm_identifiers.append({"config": cfg, "value": str(val)})
            cleaned["identifiers"] = norm_identifiers
        return cleaned

    def resolve_foreign_keys(self, rec: dict[str, Any]) -> dict[str, Any]:
        geo_external = rec.get("geo_organization")
        if geo_external:
            org = Organization.objects.filter(external_id=geo_external).first()
            if not org:
                msg = f"geo_organization with external_id '{geo_external}' not found"
                raise ValueError(msg)
            rec["geo_organization"] = org
        else:
            rec["geo_organization"] = None
        return rec

    def handle(self, *args, **options):
        source = options["source"]
        records = self._load_records(source)
        total, normalized, errors = self._preprocess_records(records, options)
        if total == 0:
            return
        created, updated, failed = self._process_records(normalized, options)
        self._print_final_summary(total, created, updated, failed, len(errors))

    # Helper methods added below
    def _process_records(
        self, normalized: list[dict[str, Any]], options: dict
    ) -> tuple[int, int, int]:
        created = updated = failed = 0
        batch_size = options["batch_size"]
        batch: list[dict[str, Any]] = []
        last_progress_print = 0

        def print_progress(force: bool = False):
            nonlocal last_progress_print, created, updated, failed
            processed = created + updated + failed
            if force or processed - last_progress_print >= PROGRESS_INTERVAL:
                last_progress_print = processed
                pct = (processed / max(1, len(normalized))) * 100 if normalized else 0
                self.stdout.write(
                    f"Progress: {processed}/{len(normalized)} ({pct:0.1f}%) | Created: {created} Updated: {updated} Failed: {failed}\r",
                    ending="",
                )
                self.stdout.flush()

        def flush(batch_rows: list[dict[str, Any]]):
            nonlocal created, updated, failed
            if not batch_rows:
                return
            with transaction.atomic():
                for iterator in batch_rows:
                    try:
                        identifiers = iterator.pop("identifiers", None)
                        row = self.resolve_foreign_keys(iterator)
                        ext_id = row.pop("external_id")
                        obj, is_created = Patient.objects.update_or_create(
                            external_id=ext_id, defaults=row
                        )
                        if identifiers is not None:
                            self._apply_identifiers(obj, identifiers)
                        if is_created:
                            created += 1
                        else:
                            updated += 1
                    except Exception as exc:
                        failed += 1
                        ext = row.get("external_id")
                        err_msg = f"Failure for external_id={ext}: {exc}"
                        self.stderr.write(self.style.ERROR(err_msg))

        if options.get("dry_run"):
            return 0, 0, 0  # already handled earlier

        for _idx, row in enumerate(normalized, start=1):
            batch.append(row)
            if len(batch) >= batch_size:
                flush(batch)
                print_progress()
                batch = []
        flush(batch)
        print_progress(force=True)
        self.stdout.write("")  # newline after progress
        return created, updated, failed

    def _apply_identifiers(self, patient: Patient, identifiers: list[dict[str, Any]]):
        for ident in identifiers:
            config_ext = ident["config"]
            try:
                config_obj = PatientIdentifierConfig.objects.filter(
                    external_id=config_ext
                ).first()
            except Exception as e:  # pragma: no cover - safety
                msg = f"Error loading identifier config '{config_ext}': {e}"
                raise ValueError(msg) from e
            if not config_obj:
                msg = f"Identifier config '{config_ext}' not found"
                raise ValueError(msg)
            value = ident.get("value")
            ident_qs = PatientIdentifier.objects.filter(
                patient=patient, config=config_obj
            )
            existing = ident_qs.first()
            if value in (None, ""):
                if existing:
                    existing.delete()
                continue
            if not existing:
                existing = PatientIdentifier(patient=patient, config=config_obj)
            existing.value = value
            existing.facility = config_obj.facility
            existing.save()

    def _print_final_summary(
        self, total: int, created: int, updated: int, failed: int, skipped: int
    ):
        self.stdout.write(self.style.SUCCESS("Import complete"))
        self.stdout.write(f"  Total input: {total}")
        self.stdout.write(f"  Created: {created}")
        self.stdout.write(f"  Updated: {updated}")
        self.stdout.write(f"  Failed: {failed}")
        self.stdout.write(f"  Skipped (invalid pre-validation): {skipped}")
