import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from xml.dom.minidom import Identified

import requests
from dateutil.parser import isoparse
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from care.emr.models import Organization, Patient
from care.emr.models.patient import PatientIdentifier, PatientIdentifierConfig
from care.emr.utils.auto_time import disable_auto_time
from care.users.models import User

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
    # Creator / updater external IDs (UUID strings). Optional.
    "created_by",
    "updated_by",
]
EXTRA_FIELDS = [
    "identifiers",  # List[{"config": <config_external_id>, "value": <str>}] (optional)
    "created_date",  # ISO8601 datetime
    "modified_date",  # ISO8601 datetime
]
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS + EXTRA_FIELDS


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
            if resp.status_code != 200:
                raise CommandError(
                    f"Failed to download {source}: HTTP {resp.status_code}"
                )
            return resp.text, True
        # treat as file path
        path = Path(source).expanduser()
        if not path.exists():
            raise CommandError(f"File not found: {path}")
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

    def normalize_record(self, rec: dict[str, Any]) -> dict[str, Any]:
        """Validate required fields and basic structure.

        Supports optional 'identifiers' list with objects having 'config' and 'value'.
        """
        cleaned = {k: v for k, v in rec.items() if k in ALL_FIELDS}
        missing = [f for f in REQUIRED_FIELDS if not cleaned.get(f)]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        identifiers = cleaned.get("identifiers") or []
        if identifiers and not isinstance(identifiers, list):
            raise ValueError("'identifiers' must be a list")
        validated_identifiers: list[dict[str, Any]] = []
        for i, ident in enumerate(identifiers, start=1):
            if not isinstance(ident, dict):
                raise ValueError(f"identifiers[{i}] must be an object")
            cfg = ident.get("config")
            # value may be empty -> indicates deletion when updating
            if not cfg:
                raise ValueError(f"identifiers[{i}].config is required")
            validated_identifiers.append({"config": cfg, "value": ident.get("value")})
        if validated_identifiers:
            cleaned["identifiers"] = validated_identifiers

        # Validate optional created_date / modified_date for dry-run visibility
        for dt_field in ("created_date", "modified_date"):
            if cleaned.get(dt_field):
                try:
                    dt = (
                        isoparse(cleaned[dt_field])
                        if isinstance(cleaned[dt_field], str)
                        else cleaned[dt_field]
                    )
                    if timezone.is_naive(dt):  # make timezone aware
                        dt = timezone.make_aware(dt)
                    cleaned[dt_field] = dt
                except Exception as exc:
                    raise ValueError(f"Invalid {dt_field}: {exc}") from exc

        # created_by / updated_by are user external_ids. We'll resolve later.
        for user_field in ("created_by", "updated_by"):
            if user_field in cleaned and cleaned[user_field] in (None, ""):
                # Treat empty string as an explicit null (no change on update)
                cleaned.pop(user_field, None)
        return cleaned

    def handle(self, *args, **options):
        enable_auto_time = disable_auto_time(Patient, Identified)

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
                rec = self.normalize_record(rec)
                normalized.append(rec)
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

        id_config_cache: dict[str, int] = dict(
            PatientIdentifierConfig.objects.values_list("external_id", "id")
        )
        user_cache: dict[str, int] = dict(User.objects.values_list("external_id", "id"))
        geo_org_cache: dict[str, int] = {}

        batch_size = options["batch_size"]
        batch: list[dict[str, Any]] = []

        def flush(batch: list[dict[str, Any]]):
            nonlocal created, updated, failed
            if not batch:
                return
            with transaction.atomic():
                for rec in batch:
                    try:
                        identifiers = rec.pop("identifiers", [])  # custom field
                        created_by_ext = rec.pop("created_by", None)
                        updated_by_ext = rec.pop("updated_by", None)
                        if geo_org_ext := rec.pop("geo_organization", None):
                            if geo_org_ext in geo_org_cache:
                                rec["geo_organization_id"] = geo_org_cache[geo_org_ext]
                            else:
                                org = Organization.objects.filter(
                                    external_id=geo_org_ext
                                ).first()
                                if not org:
                                    raise ValueError(
                                        f"geo_organization with external_id '{geo_org_ext}' not found"
                                    )
                                geo_org_cache[geo_org_ext] = org.id
                                rec["geo_organization_id"] = org.id
                        ext_id = rec.pop("external_id")
                        int_id = rec.pop("id", None)

                        # Resolve created_by / updated_by external UUIDs to User objects if provided
                        if created_by_ext:
                            user_obj_id = user_cache[created_by_ext]
                            rec["created_by_id"] = user_obj_id
                        if updated_by_ext:
                            user_obj_id = user_cache[updated_by_ext]
                            rec["updated_by_id"] = user_obj_id
                        patient_obj, is_created = Patient.objects.update_or_create(
                            id=int_id, defaults=rec
                        )
                        # Process identifiers after patient is saved
                        update_ident_cache = False
                        if identifiers:
                            for ident in identifiers:
                                cfg_ext = ident["config"]
                                value = ident.get("value")
                                try:
                                    cfg_id = id_config_cache[cfg_ext]
                                    ident_qs = PatientIdentifier.objects.filter(
                                        patient=patient_obj, config_id=cfg_id
                                    )
                                    ident_obj = ident_qs.first()
                                    if not value:
                                        # Deletion request
                                        if ident_obj:
                                            ident_obj.delete()
                                        update_ident_cache = True
                                        continue
                                    if not ident_obj:
                                        ident_obj = PatientIdentifier(
                                            patient=patient_obj,
                                            config_id=cfg_id,
                                        )
                                    if ident_obj.value != value:
                                        ident_obj.value = value
                                        ident_obj.save()
                                        update_ident_cache = True
                                except Exception as ident_exc:
                                    raise ValueError(
                                        f"Identifier '{cfg_ext}' failed: {ident_exc}"
                                    ) from ident_exc
                            # rebuild patient identifier cache json fields
                            if update_ident_cache:
                                patient_obj.build_instance_identifiers()
                                patient_obj.save()
                        if is_created:
                            created += 1
                        else:
                            updated += 1
                    except Exception as exc:
                        failed += 1
                        self.stderr.write(
                            self.style.ERROR(
                                f"Failure for external_id={rec.get('external_id') or ext_id}: {exc}"
                            )
                        )

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
                    ending="",
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

        enable_auto_time()
