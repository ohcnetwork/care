---
title: Unresolved Items
document: inventory/unresolved-items
version: 0.2.0
status: Draft
phase: 0
source_repository: https://github.com/ohcnetwork/care
source_branch: gcp
source_commit: 6a2976dc2512c2c532fcc70628c5690fbbbe3f3d
baseline_commit: 2fe40cd16
reviewed: 2026-08-06
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
| 1933 | `docs/xii/architecture/02-target-runtime.md` |
| 1945 | `docs/xii/architecture/02-target-runtime.md` |

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

**Partly resolved in IS-01.** The `patient` and `report` storage aliases now read
`FILE_UPLOAD_REGION`, `FILE_UPLOAD_KEY` and `FILE_UPLOAD_SECRET`, so those three
settings are no longer dead and per-bucket credentials are configurable.
`get_patient_bucket_config` and `get_report_bucket_config` still contain the
original defect, but are now reached only by the legacy signed-URL path, which
IS-02 removes. See `storage-call-sites.md` §11.4 for the behaviour change.

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

### B10. `delete_objects` is dead code — RESOLVED (IS-01)

**verified** `care/emr/utils/file_manager.py:112-133` had no caller and carried a
GCP-specific `NotImplemented` branch.

**Removed in IS-01.** It was deleted rather than ported: it had no caller, and
ES-01 §17 forbids provider-specific batch calls. Django Storage defines no
portable bulk delete; a future caller should iterate `Storage.delete()`.

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

## Part B2 — Storage issues open after IS-01

Recorded 2026-08-06. Only issues that remain genuinely unresolved after the
storage seam moved onto Django Storage. Full detail in
`storage-call-sites.md` §11.

### S1. The GCS profile cannot serve files end to end — RESOLVED (2026-08-07)

**Was:** `care/emr/utils/legacy_signed_urls.py` constructed a boto3 client
directly and was S3-only, so `CARE_STORAGE_BACKEND=gcs` configured persistence
against Google Cloud Storage while both signed-URL flows silently kept pointing
at S3/MinIO — and at the *old* bucket names, since they resolved buckets through
the now-deleted `care/utils/csp/`.

**Resolved** by removing the signed-URL transport outright rather than porting
it. CARE now serves every object through Django Storage, so `download_url`
carries neither a provider nor a bucket and both profiles behave identically.
Verified under `gcs`: persistence resolves to `GoogleCloudStorage` and
`download_url` is still `/api/v1/files/{id}/download/`.

**Consequence:** IS-02 is no longer a prerequisite for a GCS deployment. Only S2
below stands between the `gcs` profile and production use — and until S2 is
closed, *report generation* SHALL NOT be described as production-ready under
`gcs`, even though the rest of the file surface is. See
`02-target-runtime.md` §11.

### S2. Report generation does not retry under GCS

**verified** `care/emr/tasks/report_generation.py:13` uses
`autoretry_for=(ClientError,)`. Under `s3` this still works, because
django-storages raises `botocore` errors from inside `Storage.save`. Under `gcs`
the failures are `google.api_core.exceptions.*` and no retry occurs.

**Impact (verified):** it does not degrade to "retries less often" — it degrades
to **no retry at all**, silently. The task carries a retry policy that cannot
fire, so the first transient upload failure fails the report, and nothing in the
logs distinguishes that from a policy that fired and exhausted itself.

**Not changed** — both ES-01 §31 and the completion pass explicitly forbid
modifying Celery, and widening `autoretry_for` alters retry semantics beyond the
storage seam. `02-target-runtime.md` §11 records the two acceptable resolutions
and forbids claiming GCS report generation is production-ready until one lands.

**Now the only item blocking the GCS profile**, and the last provider-specific
reference in any storage consumer. **Decision needed:** a provider-neutral retry
predicate, or an explicit translation at the storage boundary. Report generation
still succeeds under `gcs`; only retry-on-transient-failure is absent.

### S3. Overwrite safety depends on a backend option, not on Django Storage

**verified** `Storage.save()` renames on collision unless the backend is
configured otherwise; `InMemoryStorage` demonstrably does. CARE relies on
overwrite semantics, which are supplied by `file_overwrite: True` on each alias
in `config/storage.py`.

**inferred** Any future alias, or any backend swapped in for testing, must set it
or CARE will silently write to a renamed object while the database keeps the
original `internal_name`. Asserted in `care/utils/tests/test_storage_config.py`.

### S4. Still true after IS-01, unchanged by it

These were recorded in Part B and remain accurate; IS-01 changed the persistence
call underneath them but not the behaviour:

| # | Item | Note |
| --- | --- | --- |
| B4 | `cleanup_incomplete_file_uploads` aborts the batch on one storage error | Semantics preserved deliberately, per ES-01 §17 |
| B5 | Report generation is not idempotent under retry | Untouched |
| B8 | Storage writes are not covered by the surrounding transaction | Untouched; still orphans objects on commit failure |
| B9 | `mark_upload_completed` trusts the client | **Largely defused.** No client can write to the bucket any more, so a file marked complete without one is now only a bookkeeping inconsistency, not an unverified external write. The endpoint is redundant; IS-02 decides its fate |

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

**RESOLVED by IS-01 — they stay publicly *readable*, but the bucket does not.**
No object carries an ACL any more. The bytes are served by CARE through two
anonymous routes, `facility-cover-image-asset` and `user-profile-picture-asset`
(`care/emr/api/viewsets/file_assets.py`), so who can see a cover image is
unchanged while the bucket becomes private and GCS uniform bucket-level access
is satisfied.

Both URL builders now `reverse()` to those routes. `FACILITY_CDN` and
`BUCKET_HAS_FINE_ACL` were deleted rather than redefined: with CARE serving the
bytes, a CDN belongs in front of CARE, which the long-lived `Cache-Control` on
those responses allows.

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

**Still open after IS-01.** The endpoint moved to
`care/emr/api/viewsets/file_upload.py:230` and its persistence now goes through
Django Storage, but it is unchanged as transport: it still takes a base64
`file_data` string, still buffers the decoded file in memory, and still carries
no `@extend_schema`, with its body fields read straight from `request.data`.

**inferred** Schema-generated clients cannot discover it. Whether it is
public API or an internal affordance is **unknown**.

The new `download` action *is* annotated, so the download half of the contract
is discoverable while the upload half is not. IS-02 owns closing this, together
with replacing the base64 body — annotating a body that is about to change would
be wasted work.

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
| ~~D8~~ | ~~Green baseline test count and duration~~ | **Resolved 2026-08-06** — 1912 tests, 0 skipped, ~21-29 s with `--keepdb --parallel`; see `runtime-and-deployment.md` §11.9 |

---

## Part E — Baseline blockers

**RESOLVED 2026-08-06.** A green baseline exists. Full record in
`runtime-and-deployment.md` §11.

Baseline: commit `2fe40cd16`, all five compose services healthy, 312 migrations
applied, `makemigrations --check` clean, fixtures loaded, **1912 tests, 0 skipped**,
green on 2 of 3 runs. See E7 for the single flake.

Disposition of the blockers recorded in the previous revision:

| # | Blocker | Disposition |
| --- | --- | --- |
| E1 | Docker daemon not running | **resolved** — Docker Desktop started; engine 29.6.2, Compose v5.3.1 |
| E2 | `make` not installed | **not a blocker** — every `Makefile` target was translated to its underlying `docker compose` command; see `runtime-and-deployment.md` §11.3 |
| E3 | No Python environment | **not applicable** — all execution happens inside the container |
| E4 | Host Python 3.14.5 vs required `==3.13.*` | **not applicable** — the image ships Python 3.13.14 |
| E5 | Redis not running | **resolved** — supplied by the compose `redis` service, healthy |
| E6 | `.env` absent | **withdrawn — the claim was wrong.** No root `.env` is required. `docker compose config` resolves with no warnings; every interpolation has a default. The real env files, `docker/.local.env` and `docker/.prebuilt.env`, are **tracked in git**. There are no `.example` variants of either. |

### E7. Shared-Redis test isolation failures under `--parallel`

**Scope corrected 2026-08-06 (during IS-01).** Originally recorded as a single
flaky test. It is a defect *class* affecting at least **six** tests in **two**
families, and it fires far more often than the first sample suggested.

**verified** Root cause: `config/settings/test.py:45-56` points the cache at
Redis with a single `KEY_PREFIX = "test_"`, shared by all 16 parallel workers,
while `cache.clear()` runs in `setUp` at `care/emr/tests/test_reset_password_api.py:24`
and `care/emr/tests/test_valueset_api.py:23, 52`. A clear in one worker discards
cache state another worker is mid-way through asserting on.

**verified** Affected tests observed failing:

| Family | Test | Mechanism |
| --- | --- | --- |
| Rate limiting | `test_password_request_rate_limiting` | `config/ratelimit.py:9` returns the constant key `"ratelimit"`, so the counter is global and a concurrent clear resets it — `200 != 429` |
| Rate limiting | `test_password_check_rate_limiting` | same |
| Rate limiting | `test_password_confirm_rate_limiting` | same |
| Favorites | `test_add_favorite` | asserts on values read back from the shared cache (`care/emr/api/viewsets/favorites.py:40-56`) |
| Favorites | `test_remove_favorite_single` | same |
| Favorites | `test_favorite_lists_returns_list_on_first_call` | same |

**verified** Measured on `feature/django-storages` at 1962 tests:

| Configuration | Result |
| --- | --- |
| Full suite, serial (`--shuffle`, no `--parallel`) | **1962/1962 OK** |
| Full suite, `--parallel --shuffle`, 6 runs | 1 green, 5 with 1-2 failures |
| Only `test_favorites_api`, `test_valueset_api`, `test_reset_password_api` in parallel, 4 runs | **4/4 failed** (76 tests, no storage code involved) |

**verified** That last row is the decisive one: the defect reproduces with the
three cache-touching modules alone, so it is independent of any other change.

**inferred** The observed rate rose from 1-in-3 during the Phase 0 baseline to
5-in-6 here. No cache, lock or rate-limit code changed between the two. The
likeliest explanation is scheduling: more tests and slower ones (MinIO round
trips) alter how work is distributed across the 16 workers and widen the window
in which a concurrent `cache.clear()` can land. The isolated reproduction above
shows the defect does not need those tests to be present at all.

**Not fixed.** ES-01 §31 explicitly excludes fixing rate limiting, and the
favorites half is equally out of scope. Upstream CI runs the same
`--parallel --shuffle` combination (`.github/workflows/reusable-test.yml:77`), so
it can occur there too. **unknown** whether it is known upstream.

**Recommended fix, for whoever owns it:** give each parallel worker its own cache
namespace, e.g. derive `KEY_PREFIX` from the worker's database suffix in
`config/settings/test.py`. That removes the whole class rather than the six
symptoms.

**inferred, separate concern:** a globally-keyed rate limit is not only a test
problem — it means the limit is shared across all callers rather than per client.

### E8. Transient wheel corruption in the BuildKit pip cache

**verified** The first image build failed with
`zipfile.BadZipFile: Bad CRC-32 for file '_brotli.cpython-313-x86_64-linux-gnu.so'`
during `pipenv install` at `docker/dev.Dockerfile:22`.

**verified** Resolved by pruning only BuildKit cache mounts
(`docker builder prune --filter type=exec.cachemount`). The rebuild succeeded and
it has not recurred. **inferred** transient corruption, not a repository defect —
recorded only so the same symptom is recognised quickly if it reappears.
