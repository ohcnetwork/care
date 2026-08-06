---
title: Unresolved Items
document: inventory/unresolved-items
version: 0.1.0
status: Draft
phase: 0
source_repository: https://github.com/ohcnetwork/care
source_branch: gcp
source_commit: 6a2976dc2512c2c532fcc70628c5690fbbbe3f3d
reviewed: 2026-08-05
---

# Unresolved Items

Open questions, code defects found while inventorying, and contradictions between
the existing GCP documents and the verified state of the repository.

Nothing here was fixed in Phase 0. Each item states what is **verified**, what is
**inferred**, and what remains **unknown**.

---

## Part A — Contradictions with existing documents

Per the Phase 0 brief, the other GCP documents were not rewritten. Where a
verified code fact contradicts them, it is recorded here instead.

### A1. Document paths are inconsistent across the set

**verified** The eight architecture documents live at
`docs/xii/architecture/`. They were committed there in `e280e0f09`.

**verified** `01-current-runtime.md` referenced two *different* wrong paths for
the same target document:

| Line (before correction) | Text |
| --- | --- |
| 1933 | `docs/gcp/02-target-runtime.md` |
| 1945 | `docs/xii/gcp/02-target-runtime.md` |

**Corrected** in this phase — both now read `docs/xii/architecture/02-target-runtime.md`.

**unknown** Whether the other seven documents contain the same wrong paths. Not
audited; only `01-current-runtime.md` was in scope. **Recommend** a path sweep
across all eight before they are published.

### A2. `01-current-runtime.md` was wrapped in a broken code fence

**verified** Before correction the file opened with a stray ```` ````markdown ````
at line 1 and closed the fence at line 35 with four backticks, where three were
required to close the inner `text` block. Two further stray ` ``` ` lines sat at
the end of the file.

**verified consequence** The YAML frontmatter and all of sections 1-2 rendered as
literal code rather than as document content, and the entire tail of the file sat
inside an unterminated block.

**Corrected** in this phase.

### A3. `01-current-runtime.md` §38 misstated patient-bucket credentials

**verified** The document listed `FILE_UPLOAD_REGION`, `FILE_UPLOAD_KEY` and
`FILE_UPLOAD_SECRET` as the settings patient files use.

**verified** They are not. `get_patient_bucket_config`
(`care/utils/csp/config.py:46-56`) reads `FACILITY_S3_REGION`, `FACILITY_S3_KEY`
and `FACILITY_S3_SECRET`. The three `FILE_UPLOAD_*` credential settings
(`config/settings/base.py:537-539`) are read by no code in the repository.

**Corrected** in this phase. See also §2 below for the underlying defect.

### A4. `01-current-runtime.md` §26 omitted three task definitions

**verified** The document inventoried `care/emr/tasks/` accurately but did not
mention the three task-decorated functions defined elsewhere:
`handle_cascade` (`care/emr/models/location.py:159`),
`summarise_monetary_components` (`care/emr/models/resource_category.py:123`),
and `rebalance_account_task` (`care/emr/resources/account/sync_items.py:81`).

**Corrected** in this phase with a descriptive addition only.

### A5. The stated goal "keep Redis optional" is not currently supportable

**verified** Three hard couplings prevent it, detailed in `cache-and-redis.md` §1:
`cache.set(..., nx=True)` (`care/utils/lock.py:18, 44`),
`cache.delete_pattern(...)` (`care/emr/resources/base.py:313, 315`), and
`get_redis_connection("default")` (`care/emr/models/valueset.py:77`).

**inferred** This does not contradict the *goal*, but it does contradict any
document that treats Redis removal as configuration. It is schema and code work.

**unknown** Whether `02-target-runtime.md` or `03-migration-plan.md` make that
assumption. Not audited.

### A6. "All uploads pass through Django" is partly already true

**verified** `POST /api/v1/files/upload-file/`
(`care/emr/api/viewsets/file_upload.py:213-270`) already proxies uploads through
Django as base64.

**inferred** Any document describing the Django-proxied upload as new work should
account for this endpoint — the task is to replace a base64 path with a streaming
one and to remove the presigned alternative, not to build from nothing.

---

## Part B — Code defects found during inventory

These are pre-existing upstream issues, not regressions. None was fixed.

### B1. Patient and report buckets use facility credentials

**verified** `care/utils/csp/config.py:46-56` and `:59-70` set
`aws_access_key_id` / `aws_secret_access_key` from `FACILITY_S3_KEY` /
`FACILITY_S3_SECRET` while returning `settings.FILE_UPLOAD_BUCKET` as the bucket.

**verified** `FILE_UPLOAD_REGION`, `FILE_UPLOAD_KEY`, `FILE_UPLOAD_SECRET`
(`config/settings/base.py:537-539`) are dead settings.

**Impact (inferred):** per-bucket credential separation is impossible today. A
GCP design assuming distinct service accounts or HMAC keys per bucket must fix
this first. Note the *endpoint* settings are wired correctly, so the bug is
invisible in single-credential local and MinIO setups — which is likely why it
has survived.

**unknown** Whether this is intentional consolidation or an unnoticed
copy-paste. **Recommend** raising upstream before diverging.

### B2. LocMem/Dummy cache shims silently disable locking

**verified** `config/caches.py:6-9` and `:12-16` accept the `nx` kwarg, ignore it,
and unconditionally `return True`.

**verified** `Lock.acquire` (`care/utils/lock.py:17-19`) treats any truthy return
as success. Under either shim, **no lock is ever contended**.

**verified** The shims are referenced only from `care/utils/tests/test_utils.py:18`.

**Impact (inferred):** the most dangerous item in this document. Substituting a
PostgreSQL or LocMem cache backend does not degrade locking — it removes it,
silently, with call sites that still read as correct. Any PostgreSQL lock must be
a real conditional write (`INSERT ... ON CONFLICT DO NOTHING` or
`pg_try_advisory_lock`).

### B3. Redis outage accepts revoked JWTs

**verified** `config/settings/base.py:93` sets `IGNORE_EXCEPTIONS: True`.

**verified** `config/authentication.py:21` treats a cache miss as
"token not invalidated".

**Impact (inferred):** with Redis unreachable, `cache.get` returns `None` and
revoked access tokens are honored. This is a security property degrading open.
Contrast with `Lock.acquire`, which degrades closed under the same condition.

**unknown** Whether this is a known accepted risk upstream.

### B4. `cleanup_incomplete_file_uploads` aborts the batch on one storage error

**verified** `care/emr/tasks/cleanup_incomplete_file_uploads.py:34-40` logs and
then re-raises inside the per-file loop, **before**
`ids_to_delete.append(file.id)` at line 41.

**verified** `quiet=True` only suppresses `NoSuchKey`
(`care/emr/utils/file_manager.py:106`); any other `ClientError` propagates.

**Impact (inferred):** one undeletable object stalls the entire cleanup
indefinitely. Rows already deleted from storage in that page are never removed
from the database, so the next run retries them — self-healing but non-progressing.

### B5. Report generation is not idempotent under retry

**verified** `care/emr/tasks/report_generation.py:12-14` declares
`autoretry_for=(ClientError,)` with `max_retries: 3`.

**verified** `care/emr/reports/report_utils.py:102, 104-121` creates a **new**
`ReportUpload` row and a new object key on every invocation.

**Impact (inferred):** each retry produces an additional row and stored object.
The failure path deletes the row only when `put_object` itself raises
(`report_utils.py:129-131`); a crash between the row save (`:121`) and the
`put_object` (`:124`) leaves an orphan.

### B6. `expires` and `max_retries` interact badly

**verified** `report_generation.py:13` and `totp.py:11, 38` all set
`expires=10 * 60` alongside `max_retries: 3`.

**inferred** A task that expires 10 minutes after dispatch can have queued
retries discarded on expiry, so the effective retry count is less than 3 whenever
the queue is backed up. Not verified against Celery's exact expiry semantics for
retried tasks. **unknown** whether the interaction was considered.

### B7. TOTP emails retry on any exception, including post-send failures

**verified** `care/emr/tasks/totp.py:9` and `:36` use
`autoretry_for=(Exception,)`.

**verified** `msg.send()` is the last statement (`:32`, `:59`).

**inferred** A failure after the SMTP handoff but before task completion
re-sends the email. Low severity, but relevant if Cloud Tasks changes retry
timing.

### B8. Storage writes are not covered by the surrounding transaction

**verified** `care/emr/api/viewsets/file_upload.py:255-268` wraps the model save
and `put_object` in one `transaction.atomic()` block.

**inferred** Object storage is not transactional. A commit failure after a
successful `put_object` orphans the object; the DB row rolls back but the bytes
remain. `cleanup_incomplete_file_uploads` does not catch these, because it keys
off `FileUpload` rows — and the row no longer exists.

### B9. `mark_upload_completed` trusts the client

**verified** `care/emr/api/viewsets/file_upload.py:177-184` sets
`upload_completed = True` with no check that an object exists in the bucket.

**inferred** Inherent to the presigned-PUT design: Django never observes the
upload. A Django-proxied upload path removes this class of problem entirely.

### B10. `delete_objects` is dead code

**verified** `care/emr/utils/file_manager.py:112-133` has no caller. Grep returns
only the definition.

**verified** It already carries a GCP-specific `NotImplemented` branch
(`:128-133`).

**inferred** Delete rather than port.

### B11. Celery beat health check is a liveness lie

**verified** `scripts/celery_beat.sh` runs `touch /tmp/healthy` **before**
exec'ing `celery beat`.

**verified** `scripts/healthcheck.sh` probes the beat role with `ls /tmp/healthy`.

**inferred** The marker persists after beat dies, so the container reports healthy
while scheduling nothing. Low relevance under Cloud Run (no beat), but it means
the current runtime may have silently failing schedules.

### B12. Dead cache import shadowed by a local variable

**verified** `care/facility/models/facility.py:4` imports
`from django.core.cache import cache`, never calls it, and binds a local
`cache = []` at line 226 inside `sync_cache`.

**Impact:** cosmetic. Recorded because it produces a false positive in any
cache-usage grep.

---

## Part C — Open questions requiring a decision

### C1. Where do migrations run under Cloud Run?

**verified** Today, `migrate` runs only in `scripts/celery_beat.sh` and
`scripts/celery-dev.sh`. The API containers never migrate.
`Procfile:2` defines a `release` phase, but no Docker path uses it.

**Decision needed.** Cloud Run Job, deploy step, or an init container. Must also
cover `sync_permissions_roles` and `sync_valueset`, which run in the same scripts
— and the first depends on the Redis lock from B2.

### C2. Do cover images and avatars remain public?

**verified** Written with `ACL: public-read` when `BUCKET_HAS_FINE_ACL` is set
(`care/utils/file_uploads/cover_image.py:49-51`); read via unsigned concatenated
URLs (`care/facility/models/facility.py:207-212`, `care/users/models.py:202-207`).

**Decision needed.** GCS uniform bucket-level access rejects per-object ACLs. If
these become private, both URL builders need Django routes, and `FACILITY_CDN`
(`config/settings/base.py:673`) needs a new meaning.

### C3. Is the API allowed to start without Redis?

**verified** `scripts/start.sh` and `scripts/start-dev.sh` both call
`wait_for_redis.sh`.

**Decision needed.** Retaining the wait makes Redis a hard Cloud Run cold-start
dependency. Removing it contradicts `IGNORE_EXCEPTIONS: True` only in spirit —
but see B3 for the security consequence of tolerating a missing Redis.

### C4. Does the Celery result backend get ported at all?

**verified** `CELERY_RESULT_BACKEND = CELERY_BROKER_URL`
(`config/settings/base.py:423`); no `AsyncResult` anywhere; no caller reads a
task result or ID.

**inferred** It can be dropped. Flagged because dropping it is cheap and removes
a Redis dependency outright.

### C5. What replaces the Celery queue-length health check?

**verified** `config/settings/base.py:458-466` constructs
`DjangoCeleryQueueLengthHealthCheck` with `broker=REDIS_URL`.

**Decision needed.** Under Cloud Tasks there is no Redis queue. Left as-is, the
health endpoint reports unhealthy in the target runtime.

### C6. Email delivery on GCP

**verified** `Pipfile` installs `django-anymail` with the `amazon-ses` extra.

**Decision needed.** GCP has no SES equivalent. Options are keeping SES
cross-cloud, or switching provider — which changes `EMAIL_BACKEND` and the
Anymail extra.

### C7. Celery's hardcoded `Asia/Kolkata` timezone

**verified** `config/celery_app.py:16` sets `enable_utc=False` and
`timezone="Asia/Kolkata"`, overriding `CELERY_TIMEZONE`
(`config/settings/base.py:417-419`).

**Decision needed.** `crontab(hour="0", minute="0")`
(`care/emr/tasks/__init__.py:14`) means midnight IST. Cloud Scheduler needs that
made explicit rather than inherited.

### C8. `ADDITIONAL_PLUGS` must match at build and deploy

**verified** Consumed at image build (`docker/prod.Dockerfile:39`) to `pip install`,
and again at every process start (`config/settings/base.py:19`) to populate
`INSTALLED_APPS`.

**verified** Invalid JSON is logged and swallowed (`plugs/manager.py:27-28`).

**Decision needed.** A mismatch yields `ModuleNotFoundError` at startup; a typo
yields silent plugin loss. Both warrant an explicit startup assertion.

### C9. `internal_name` exposure

**verified** `care/emr/resources/file_upload/spec.py:108` returns
`internal_name` — the storage object key — carrying the in-source comment
`# Not sure if this needs to be returned`.

**Decision needed.** Low risk while the bucket is private; unnecessary surface
either way.

### C10. Base64 upload endpoint is missing from the OpenAPI schema

**verified** `care/emr/api/viewsets/file_upload.py:213` has no `@extend_schema`;
its body fields are read straight from `request.data`.

**inferred** Schema-generated clients cannot discover it. Whether it is
public API or an internal affordance is **unknown**.

---

## Part D — Unknowns not resolvable from this repository

| # | Unknown | Why |
| --- | --- | --- |
| D1 | Which frontend components consume `signed_url` / `read_signed_url` | Frontend is a separate repository |
| D2 | Whether any client uses the base64 `upload-file` endpoint | Absent from OpenAPI; no caller here |
| D3 | Which plugins a given deployment installs | Governed by `ADDITIONAL_PLUGS`, outside version control |
| D4 | Whether known CARE plugins are GCP-compatible | No plugin source vendored |
| D5 | Meaning of `PLUGIN_CONFIGS` keys | No consumer in this repository |
| D6 | Typical file sizes and report generation duration | No instrumentation or metrics in the repository |
| D7 | Whether B1 and B3 are known upstream | Requires checking the upstream issue tracker |
| D8 | Green baseline test count and duration | Baseline blocked — see `runtime-and-deployment.md` §11 |

---

## Part E — Baseline blockers

**verified** No baseline command was executed. Full detail in
`runtime-and-deployment.md` §11.

| # | Blocker | Evidence |
| --- | --- | --- |
| E1 | Docker daemon not running | `docker info` → cannot connect to `npipe:////./pipe/dockerDesktopLinuxEngine` |
| E2 | `make` not installed | `make --version` → command not found |
| E3 | No Python environment | no `.venv`; no `pipenv`; `import django` fails |
| E4 | Host Python is 3.14.5, project requires `==3.13.*` | `pyproject.toml:22` |
| E5 | Redis not running | `localhost:6379` refused; `config/settings/test.py:45-46` requires it |
| E6 | `.env` absent | `Makefile` and compose both expect it |

**This is the highest-priority item in this document.** Every subsequent phase
needs a green baseline to attribute failures against, and none exists.
