import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import urlparse
import sys

import requests

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from care.emr.models import Patient, Organization

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


class Command(BaseCommand):
    help = "Import patients from a JSON file (array or newline-delimited). Creates or updates by external_id."

    def add_arguments(self, parser):
        parser.add_argument(
            "source",
            type=str,
            help="Path or URL to the JSON file (list or JSONL). If URL (http/https), it will be downloaded.",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Validate and show summary without writing to DB"
        )
        parser.add_argument(
            "--strict", action="store_true", help="Fail fast on first error instead of skipping"
        )
        parser.add_argument(
            "--batch-size", type=int, default=100, help="Number of rows per DB transaction batch"
        )

    def fetch_source(self, source: str) -> Tuple[str, bool]:
        """Return the raw text content of a local path or URL.

        Returns (text, downloaded) where downloaded indicates a network fetch.
        """
        parsed = urlparse(source)
        if parsed.scheme in {"http", "https"}:
            resp = requests.get(source, timeout=60)
            if resp.status_code != 200:
                raise CommandError(f"Failed to download {source}: HTTP {resp.status_code}")
            return resp.text, True
        # treat as file path
        path = Path(source).expanduser()
        if not path.exists():
            raise CommandError(f"File not found: {path}")
        return path.read_text(), False

    def load_json(self, raw_text: str) -> Iterable[Dict[str, Any]]:
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
        records: List[Dict[str, Any]] = []
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

    def normalize_record(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        # Only keep known fields
        cleaned = {k: v for k, v in rec.items() if k in ALL_FIELDS}
        missing = [f for f in REQUIRED_FIELDS if not cleaned.get(f)]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        return cleaned

    def resolve_foreign_keys(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        geo_external = rec.get("geo_organization")
        if geo_external:
            org = Organization.objects.filter(external_id=geo_external).first()
            if not org:
                raise ValueError(f"geo_organization with external_id '{geo_external}' not found")
            rec["geo_organization"] = org
        else:
            rec["geo_organization"] = None
        return rec

    def handle(self, *args, **options):
        source = options["source"]
        try:
            raw_text, downloaded = self.fetch_source(source)
            if downloaded:
                msg = f"Downloaded source from {source}"
                if hasattr(self.style, 'NOTICE'):
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

        normalized: List[Dict[str, Any]] = []
        errors: List[str] = []
        for idx, rec in enumerate(records, start=1):
            try:
                rec = self.normalize_record(rec)
                normalized.append(rec)
            except Exception as exc:
                msg = f"Row {idx}: {exc}"
                if options["strict"]:
                    raise CommandError(msg)
                errors.append(msg)

        if errors:
            self.stdout.write(self.style.WARNING(f"Skipped {len(errors)} invalid rows (use --strict to fail):"))
            for e in errors[:10]:  # show sample
                self.stdout.write("  - " + e)
            if len(errors) > 10:
                self.stdout.write(f"  ... {len(errors) - 10} more")

        created = 0
        updated = 0
        failed = 0

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry run summary:"))
            self.stdout.write(f"  Input rows: {total}")
            self.stdout.write(f"  Valid rows: {len(normalized)}")
            self.stdout.write(f"  Invalid rows: {len(errors)}")
            return

        batch_size = options["batch_size"]
        batch: List[Dict[str, Any]] = []

        def flush(batch: List[Dict[str, Any]]):
            nonlocal created, updated, failed
            if not batch:
                return
            with transaction.atomic():
                for rec in batch:
                    try:
                        rec = self.resolve_foreign_keys(rec)
                        ext_id = rec.pop("external_id")
                        obj, is_created = Patient.objects.update_or_create(
                            external_id=ext_id, defaults=rec
                        )
                        if is_created:
                            created += 1
                        else:
                            updated += 1
                    except Exception as exc:
                        failed += 1
                        self.stderr.write(self.style.ERROR(f"Failure for external_id={rec.get('external_id')}: {exc}"))

        last_progress_print = 0
        def print_progress(force=False):
            nonlocal last_progress_print
            # print every 100 records or on force
            processed = created + updated + failed
            if force or processed - last_progress_print >= 100:
                last_progress_print = processed
                pct = (processed / max(1, len(normalized))) * 100
                self.stdout.write(
                    f"Progress: {processed}/{len(normalized)} ({pct:0.1f}%) | Created: {created} Updated: {updated} Failed: {failed}\r",
                    ending=""
                )
                self.stdout.flush()

        for idx, rec in enumerate(normalized, start=1):
            batch.append(rec)
            if len(batch) >= batch_size:
                flush(batch)
                print_progress()
                batch = []
        flush(batch)
        print_progress(force=True)
        # Move to next line after carriage returns
        self.stdout.write("")

        self.stdout.write(self.style.SUCCESS("Import complete"))
        self.stdout.write(f"  Total input: {total}")
        self.stdout.write(f"  Created: {created}")
        self.stdout.write(f"  Updated: {updated}")
        self.stdout.write(f"  Failed: {failed}")
        self.stdout.write(f"  Skipped (invalid pre-validation): {len(errors)}")
