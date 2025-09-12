import json
import uuid
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
from care.emr.models.questionnaire import (
    Questionnaire,
    QuestionnaireResponse,
)
from care.users.models import User

# ---------------------------------------------------------------------------
# Field configuration
# ---------------------------------------------------------------------------
# Required fields to create/update a QuestionnaireResponse
REQUIRED_FIELDS = [
    "external_id",  # primary identifier for upsert
    "patient",  # patient external_id
    "subject_id",  # UUID referencing the subject (e.g., patient / encounter / other domain entity)
]

OPTIONAL_FIELDS = [
    "questionnaire",  # Questionnaire external_id
    "encounter",  # Encounter external_id
    "responses",  # list (default [])
    "structured_responses",  # dict (default {})
    "structured_response_type",  # string or null
    # Optional user external_ids (UUID) for attribution
    "created_by",
    "updated_by",
]

EXTRA_FIELDS = [
    "created_date",  # ISO8601 datetime
    "modified_date",  # ISO8601 datetime
]

ALL_FIELDS = set(REQUIRED_FIELDS + OPTIONAL_FIELDS + EXTRA_FIELDS)


class Command(BaseCommand):
    help = (
        "Import questionnaire responses (QuestionnaireResponse) from a JSON array or JSONL. "
        "Creates or updates by external_id."
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
            default=200,
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
        if raw[0] == "[":
            data = json.loads(raw)
            if not isinstance(data, list):
                raise CommandError("Top-level JSON must be a list of objects")
            return data
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

        # Validate UUID subject_id
        subj = cleaned.get("subject_id")
        try:
            cleaned["subject_id"] = str(uuid.UUID(str(subj)))
        except Exception as exc:
            raise ValueError(f"Invalid subject_id UUID: {exc}") from exc

        # Defaults for optional complex fields
        if "responses" not in cleaned or cleaned.get("responses") is None:
            cleaned["responses"] = []
        if not isinstance(cleaned["responses"], list):
            raise ValueError("'responses' must be a list if provided")

        if (
            "structured_responses" not in cleaned
            or cleaned.get("structured_responses") is None
        ):
            cleaned["structured_responses"] = {}
        if not isinstance(cleaned["structured_responses"], dict):
            raise ValueError(
                "'structured_responses' must be an object (dict) if provided"
            )

        # Parse timestamp overrides (optional)
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

        # Treat empty created_by/updated_by as absent
        for user_field in ("created_by", "updated_by"):
            if user_field in cleaned and cleaned[user_field] in (None, ""):
                cleaned.pop(user_field, None)

        return cleaned

    # ------------------------------------------------------------------
    # Foreign key resolution helpers
    # ------------------------------------------------------------------
    def resolve_foreign_keys(self, rec: dict[str, Any]) -> dict[str, Any]:
        # patient
        patient_ext = rec.pop("patient")
        patient_obj = Patient.objects.filter(external_id=patient_ext).first()
        if not patient_obj:
            raise ValueError(f"Patient '{patient_ext}' not found")
        rec["patient"] = patient_obj

        # questionnaire (optional)
        if "questionnaire" in rec and rec["questionnaire"] not in (None, ""):
            questionnaire_ext = rec["questionnaire"]
            q_obj = Questionnaire.objects.filter(external_id=questionnaire_ext).first()
            if not q_obj:
                raise ValueError(f"Questionnaire '{questionnaire_ext}' not found")
            rec["questionnaire"] = q_obj
        else:
            rec["questionnaire"] = None

        # encounter (optional)
        if "encounter" in rec and rec["encounter"] not in (None, ""):
            encounter_ext = rec["encounter"]
            enc_obj = Encounter.objects.filter(external_id=encounter_ext).first()
            if not enc_obj:
                raise ValueError(f"Encounter '{encounter_ext}' not found")
            rec["encounter"] = enc_obj
        else:
            rec["encounter"] = None

        return rec

    # ------------------------------------------------------------------
    # Main handler
    # ------------------------------------------------------------------
    def handle(self, *args, **options):
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

        batch: list[dict[str, Any]] = []

        def flush(batch: list[dict[str, Any]]):
            nonlocal created, updated, failed
            if not batch:
                return
            with transaction.atomic():
                user_cache: dict[str, User | None] = {}
                for rec in batch:
                    try:
                        create_dt = rec.pop("created_date", None)
                        modify_dt = rec.pop("modified_date", None)
                        created_by_ext = rec.pop("created_by", None)
                        updated_by_ext = rec.pop("updated_by", None)
                        ext_id = rec["external_id"]
                        defaults = {k: v for k, v in rec.items() if k != "external_id"}
                        defaults = self.resolve_foreign_keys(defaults)

                        # Resolve attribution users
                        if created_by_ext:
                            if created_by_ext not in user_cache:
                                user_cache[created_by_ext] = User.objects.filter(
                                    external_id=created_by_ext
                                ).first()
                            user_obj = user_cache[created_by_ext]
                            if not user_obj:
                                raise ValueError(
                                    f"created_by user '{created_by_ext}' not found"
                                )
                            defaults["created_by"] = user_obj
                        if updated_by_ext:
                            if updated_by_ext not in user_cache:
                                user_cache[updated_by_ext] = User.objects.filter(
                                    external_id=updated_by_ext
                                ).first()
                            user_obj = user_cache[updated_by_ext]
                            if not user_obj:
                                raise ValueError(
                                    f"updated_by user '{updated_by_ext}' not found"
                                )
                            defaults["updated_by"] = user_obj
                        obj, is_created = (
                            QuestionnaireResponse.objects.update_or_create(
                                external_id=ext_id, defaults=defaults
                            )
                        )
                        ts_updates = {}
                        if is_created and create_dt:
                            ts_updates["created_date"] = create_dt
                        if modify_dt:
                            ts_updates["modified_date"] = modify_dt
                        if ts_updates:
                            QuestionnaireResponse.objects.filter(pk=obj.pk).update(
                                **ts_updates
                            )
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
            if force or processed - last_progress_print >= 200:
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
        self.stdout.write("")

        self.stdout.write(self.style.SUCCESS("Import complete"))
        self.stdout.write(f"  Total input: {total}")
        self.stdout.write(f"  Created: {created}")
        self.stdout.write(f"  Updated: {updated}")
        self.stdout.write(f"  Failed: {failed}")
        self.stdout.write(f"  Skipped (invalid pre-validation): {len(errors)}")
