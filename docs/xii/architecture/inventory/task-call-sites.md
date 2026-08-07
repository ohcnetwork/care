---
title: Task Call-Site Inventory
document: inventory/task-call-sites
version: 0.1.0
status: Draft
phase: 0
source_repository: https://github.com/ohcnetwork/care
source_branch: gcp
source_commit: 6a2976dc2512c2c532fcc70628c5690fbbbe3f3d
reviewed: 2026-08-05
---

# Task Call-Site Inventory

Every Celery task definition and dispatch site in the repository. No task was
migrated or modified in this phase.

Evidence labels: **verified** / **inferred** / **unknown**.

Classifications are restricted to the five permitted values:
`cloud_tasks_candidate`, `cloud_run_job_candidate`, `synchronous_candidate`,
`celery_compatibility`, `requires_analysis`.

---

## 1. Summary

**verified** There are **8 task definitions** in the repository.

**verified** The most consequential finding of this section: **5 of the 8 are
decorated as Celery tasks but invoked as plain Python function calls at nearly
every production call site.** They execute inline, inside the request thread,
and never reach a broker.

**verified** **4 tasks reach a broker** in non-test code, in two different ways:

- **3 are dispatched asynchronously at every call site** —
  `generate_report_task`, `send_totp_enabled_email`, `send_totp_disabled_email`.
- **1 is mixed** — `summarise_monetary_components` is called inline from
  production code but re-dispatches *itself* asynchronously in its recursive
  tail, so it reaches a broker only from inside itself.

The distinction matters for migration: the first three can move to a task
backend by changing their dispatch, while the fourth also needs its recursive
self-dispatch re-expressed, and that path has no inline equivalent to fall back
on.

**verified** Celery app: `config/celery_app.py`. Instantiated at
`celery_app.py:8` as `Celery("care")`, autodiscovery at `celery_app.py:18`.

---

## 2. Celery application configuration

**verified** `config/celery_app.py`:

| Line | Fact |
| --- | --- |
| 6 | `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")` |
| 8 | `app = Celery("care")` |
| 14 | `app.config_from_object("django.conf:settings", namespace="CELERY")` |
| 16 | `app.conf.update(enable_utc=False, timezone="Asia/Kolkata")` |
| 18 | `app.autodiscover_tasks()` |

**verified** `config/settings/production.py` exists (243 bytes).

**verified** `celery_app.py:16` **hardcodes** `timezone="Asia/Kolkata"` and
`enable_utc=False`. This overrides the `CELERY_TIMEZONE` derived from
`TIME_ZONE` at `config/settings/base.py:417-419`, because `app.conf.update` runs
after `config_from_object`. Any schedule expressed in `crontab()` is therefore
interpreted in IST regardless of deployment region.

**verified** Broker and result backend, `config/settings/base.py`:

| Setting | Line | Value |
| --- | --- | --- |
| `CELERY_BROKER_URL` | 421 | `env("CELERY_BROKER_URL", default=REDIS_URL)` |
| `CELERY_RESULT_BACKEND` | 423 | `= CELERY_BROKER_URL` (no independent env var) |
| `CELERY_TASK_TIME_LIMIT` | 432 | `1800 * 5` = 9000 s |
| `CELERY_TASK_SOFT_TIME_LIMIT` | 435 | `1800` s |
| `CELERY_ACCEPT_CONTENT` | 425 | `["json"]` |
| `CELERY_TASK_SERIALIZER` | 427 | `"json"` |

**verified** `CELERY_RESULT_BACKEND` cannot be pointed anywhere other than the
broker without a code change — `base.py:423` assigns it directly from
`CELERY_BROKER_URL`.

**verified** No `AsyncResult` usage exists anywhere in the repository. A grep for
`AsyncResult` returns zero matches in `care/` and `config/`.

**verified** No `.apply_async(` and no `send_task(` call sites exist. A grep for
both returns zero matches.

**inferred** Because no caller ever reads a result or a task ID, the result
backend is written but never consumed. This is the single strongest argument that
the result backend can be dropped rather than ported.

---

## 3. Task definitions

### 3.1 `generate_report_task`

| Field | Value |
| --- | --- |
| Source | `care/emr/tasks/report_generation.py:12-78` |
| Decorator | `@shared_task(autoretry_for=(ClientError,), retry_kwargs={"max_retries": 3}, expires=10*60)` (`:12-14`) |
| Payload | `template_id: str`, `report_type: str`, `associating_id: str`, `output_format: str = "pdf"`, `**kwargs` (`:15-21`) |
| Return value | `str(report_upload.external_id)` (`:66`) |
| Call sites | `care/emr/api/viewsets/report/report_upload.py:147` — `.delay(...)` |
| Caller uses task ID | **no** — `report_upload.py:147-157` discards the `AsyncResult` and returns HTTP 201 with an empty body |
| Caller reads result | **no** |
| Retry policy | 3 retries, only on `botocore` `ClientError` (`:13`) |
| Expiry | 600 s (`:13`) |
| Duration | **unknown** — depends on WeasyPrint render time; no instrumentation in repo |
| DB effects | reads `Template` (`:39`); creates/updates/deletes `ReportUpload` via `report_utils.generate_and_upload_report` (`report_utils.py:104-133`) |
| Storage effects | `put_object` into `REPORT` bucket (`report_utils.py:124-126`) |
| Email / external | none |
| Progress state | `report_utils.set_lock` / `clear_lock` — cache-backed, see `cache-and-redis.md` §4 |
| Idempotency | **not idempotent** — each run creates a new `ReportUpload` row and a new object keyed by `uuid4()` + timestamp (`report_utils.py:102`), so a retry duplicates both. It does not *normally* orphan rows: a raising `put_object` deletes the row before re-raising (`report_utils.py:130`). Orphans are possible rather than guaranteed — they need a failure between the row save and the storage write, or one ambiguous enough that the cleanup itself does not run. See the note below. |
| Periodic | no |
| Plugin-owned | no |
| **Classification** | `cloud_tasks_candidate` |

**verified** The `expires=10*60` combined with `retry_kwargs={"max_retries": 3}`
is internally inconsistent: a task that expires after 10 minutes but retries up
to 3 times can have its retries discarded on expiry. Recorded in
`unresolved-items.md` §6.

**verified** Failure path deletes the `ReportUpload` row (`report_utils.py:130`)
but only when `put_object` raises. If the process is killed between
`report_upload.save(skip_internal_name=True)` (`:121`) and the `put_object`
(`:124`), the row survives with `upload_completed=False` and no object.

### 3.2 `send_totp_enabled_email`

| Field | Value |
| --- | --- |
| Source | `care/emr/tasks/totp.py:8-32` |
| Decorator | `@shared_task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3}, expires=10*60)` (`:8-12`) |
| Payload | `user_email: str`, `user_name: str` (`:13`) |
| Return value | `None` |
| Call sites | `care/emr/api/viewsets/totp.py:102` — `.delay(user.email, user.username)` |
| Caller uses task ID / result | **no** |
| Retry policy | 3 retries on **any** `Exception` (`:9`) |
| Expiry | 600 s (`:11`) |
| Duration | **inferred** sub-second plus SMTP round trip |
| DB effects | none |
| Storage effects | none |
| Email | **yes** — `EmailMessage(...).send()` (`:25-32`) |
| Idempotency | **not idempotent** — a retry re-sends the email. `autoretry_for=(Exception,)` is broad enough that a post-send failure would duplicate delivery. |
| Periodic | no |
| Plugin-owned | no |
| **Classification** | `cloud_tasks_candidate` |

### 3.3 `send_totp_disabled_email`

**verified** Identical shape to §3.2.

| Field | Value |
| --- | --- |
| Source | `care/emr/tasks/totp.py:35-59` |
| Decorator | `@shared_task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3}, expires=10*60)` (`:35-39`) |
| Payload | `user_email: str`, `user_name: str` (`:40`) |
| Call sites | `care/emr/api/viewsets/totp.py:139` — `.delay(user.email, user.username)` |
| Email | **yes** — `:52-59` |
| Idempotency | **not idempotent**, same reasoning as §3.2 |
| **Classification** | `cloud_tasks_candidate` |

### 3.4 `cleanup_expired_token_slots`

| Field | Value |
| --- | --- |
| Source | `care/emr/tasks/cleanup_expired_token_slots.py:12-21` |
| Decorator | `@shared_task` — bare, no retry, no expiry (`:12`) |
| Payload | none |
| Return value | `None` |
| Call sites | **periodic only** — `care/emr/tasks/__init__.py:13-17` |
| Retry policy | none |
| Expiry | none |
| Duration | **unknown** — single unbounded `queryset.delete()` (`:21`) over all expired unbooked `TokenSlot` rows |
| DB effects | **hard delete** of `TokenSlot` where `tokenbooking__isnull=True` and `end_datetime__lte=now()` (`:18-21`) |
| Storage / email | none |
| Idempotency | **idempotent** — re-running deletes nothing further |
| Periodic | `crontab(hour="0", minute="0")` — daily midnight, IST per §2 (`__init__.py:14`) |
| Plugin-owned | no |
| **Classification** | `cloud_run_job_candidate` |

**verified** Unlike `cleanup_incomplete_file_uploads`, this task does **not**
paginate. `queryset.delete()` at `:21` issues one delete over the whole matching
set. **inferred** On a large table this can exceed a request-scoped timeout,
which is why a Job rather than a Cloud Tasks handler is the right shape.

### 3.5 `cleanup_incomplete_file_uploads`

| Field | Value |
| --- | --- |
| Source | `care/emr/tasks/cleanup_incomplete_file_uploads.py:14-57` |
| Decorator | `@shared_task()` — no retry, no expiry (`:14`) |
| Payload | none |
| Return value | `True` (`:57`) |
| Call sites | periodic (`__init__.py:19-24`); test `care/emr/tests/test_file_upload_api.py:177` |
| Caller reads result | **no** — the `True` return is never consumed |
| Retry policy | none |
| Expiry | none |
| Duration | **unknown** — loops in pages of 1000 (`:21`) until the queryset is empty (`:28`) |
| DB effects | hard-deletes `FileUpload` rows (`:44`) |
| Storage effects | `delete_object` per file (`:33`), `PATIENT` bucket |
| Email | none |
| Idempotency | **idempotent** in effect — `delete_object(quiet=True)` tolerates missing keys (`:33`, and `file_manager.py:106-110`) |
| Periodic | every `FILE_UPLOAD_EXPIRY_HOURS` hours, as an **interval in seconds**, not a crontab (`__init__.py:20-24`) |
| Plugin-owned | no |
| **Classification** | `cloud_run_job_candidate` |

**verified** A defect in the loop: line 40 re-raises after logging
(`raise e` inside the `except` at `:34-40`). Because the raise happens *before*
`ids_to_delete.append(file.id)` at `:41`, one unexpected storage error aborts the
whole run and the successfully deleted objects in that page are never removed
from the database. Their rows remain with `upload_completed=False`, so the next
run retries them — self-healing, but it means a single poison object stalls
cleanup indefinitely. Recorded in `unresolved-items.md` §7.

**verified** `quiet=True` only suppresses `s3.exceptions.NoSuchKey`
(`file_manager.py:106`). Other `ClientError`s propagate and hit the `raise` above.

### 3.6 `summarise_monetary_components`

| Field | Value |
| --- | --- |
| Source | `care/emr/models/resource_category.py:123-140` |
| Decorator | `@shared_task` — bare (`:123`) |
| Payload | `category: ResourceCategory \| int` (`:124`) |
| Return value | `None` |
| Retry / expiry | none |
| **Classification** | `requires_analysis` |

**verified** Call sites — note the mixed dispatch:

| File | Line | Dispatch |
| --- | --- | --- |
| `care/emr/models/resource_category.py` | 91 | `summarise_monetary_components(self)` — **synchronous**, passes a **model instance** |
| `care/emr/models/resource_category.py` | 140 | `summarise_monetary_components.delay(component.id)` — **async**, passes an **int** |
| `care/emr/api/viewsets/resource_category.py` | 208 | `summarise_monetary_components(obj.id)` — **synchronous**, passes an **int** |

**verified** The `isinstance(category, int)` branch at `:125-126` exists precisely
because the parameter is sometimes a model instance and sometimes a primary key.

**verified** This task is **self-recursive and fans out**: line 140 dispatches one
async task per child category, and each child repeats. Depth and width are
bounded only by the `ResourceCategory` tree.

**verified** A `ResourceCategory` model instance is **not JSON-serializable**, and
`CELERY_TASK_SERIALIZER = "json"` (`base.py:427`). The `:91` call site would fail
if it were ever dispatched with `.delay()`. It works only because it is called
synchronously.

**inferred** This is why the classification is `requires_analysis`: converting the
synchronous call sites to Cloud Tasks changes a currently-transactional in-request
mutation into an eventually-consistent fan-out, and the recursive dispatch would
multiply Cloud Tasks invocations by the size of the category tree.

### 3.7 `handle_cascade`

| Field | Value |
| --- | --- |
| Source | `care/emr/models/location.py:159-167` |
| Decorator | `@app.task` — bare, uses the app object directly, imported at `location.py:9` (`from config.celery_app import app`) |
| Payload | `base_location` — a `FacilityLocation` **primary key** (`:160`, per the caller at `:128`) |
| Return value | `None` |
| Retry / expiry | none |
| DB effects | re-saves every descendant `FacilityLocation` with `update_fields=["cached_parent_json"]` (`:166`) |
| Storage / email | none |
| Periodic | no |
| Plugin-owned | no |
| **Classification** | `requires_analysis` |

**verified** Both call sites are **synchronous**:

- `care/emr/models/location.py:128` — `FacilityLocation.cascade_changes` calls
  `handle_cascade(self.id)` with no `.delay()`.
- `care/emr/models/location.py:167` — the task **recurses into itself
  synchronously**: `handle_cascade(child)`.

**verified** The recursion at `:167` passes `child`, a **`FacilityLocation`
instance**, while the entry point at `:128` passes `self.id`, an **int**. The
function body at `:165` uses the argument as `parent_id=base_location`, which
works for an int; passing a model instance relies on Django coercing the instance
to its PK in the filter. Inconsistent, but functional today.

**inferred** Since the recursion is a direct call rather than `.delay()`, the
entire subtree is walked in one synchronous pass inside whatever request or task
triggered it. Depth is bounded by the location hierarchy; Python's recursion
limit applies.

### 3.8 `rebalance_account_task`

| Field | Value |
| --- | --- |
| Source | `care/emr/resources/account/sync_items.py:81-85` |
| Decorator | `@app.task()` — imported at `sync_items.py:14` |
| Payload | `account_id` — an `Account` primary key (`:82`) |
| Return value | `None` |
| Retry / expiry | none |
| DB effects | `Account.objects.get` (`:83`), `sync_account_items(account)` (`:84`), `account.save()` (`:85`) |
| Storage / email | none |
| Periodic | no |
| Plugin-owned | no |
| **Classification** | `requires_analysis` |

**verified** **Every one of its 12 non-test call sites is synchronous.** Not one
uses `.delay()`:

| File | Lines |
| --- | --- |
| `care/emr/api/viewsets/charge_item.py` | 456 |
| `care/emr/api/viewsets/invoice.py` | 160, 224, 257, 287, 308 |
| `care/emr/api/viewsets/payment_reconciliation.py` | 95, 115, 178, 229 |
| `care/emr/resources/invoice/return_items_invoice.py` | 87, 119 |
| `care/emr/tests/test_payment_reconciliation_api.py` | 221 (test) |

**inferred** This task is financial-balance recalculation running inline in the
request path. Making it asynchronous would expose intermediate inconsistent
balances to reads. The `@app.task` decorator appears to be aspirational rather
than active — nothing in this repository dispatches it to a worker.

---

## 4. Periodic schedule

**verified** `care/emr/tasks/__init__.py:11-24`, registered on the
`current_app.on_after_finalize` signal:

| Task | Schedule | Line | Notes |
| --- | --- | --- | --- |
| `cleanup_expired_token_slots` | `crontab(hour="0", minute="0")` | 13-17 | daily 00:00, **IST** per §2 |
| `cleanup_incomplete_file_uploads` | `FILE_UPLOAD_EXPIRY_HOURS * 3600` seconds | 20-24 | interval, not crontab |

**verified** The second registration is conditional:
`if cleanup_file_upload_hours := settings.FILE_UPLOAD_EXPIRY_HOURS:`
(`__init__.py:19`). Setting `FILE_UPLOAD_EXPIRY_HOURS=0` disables the schedule
entirely. Default is `24` (`config/settings/base.py:720`).

**verified** The schedule is defined **in code**, not in a database scheduler.
There is no `django-celery-beat` dependency in `Pipfile`. The beat process holds
the schedule in memory and persists only its own timing file.

**inferred** Both schedules map cleanly to Cloud Scheduler triggers. The interval
form (`cleanup_incomplete_file_uploads`) has no anchor, so its first fire is
relative to beat startup; a Cloud Scheduler cron equivalent would need an
explicit time chosen.

---

## 5. Classification roll-up

| Classification | Count | Tasks |
| --- | --- | --- |
| `cloud_tasks_candidate` | 3 | `generate_report_task`, `send_totp_enabled_email`, `send_totp_disabled_email` |
| `cloud_run_job_candidate` | 2 | `cleanup_expired_token_slots`, `cleanup_incomplete_file_uploads` |
| `requires_analysis` | 3 | `summarise_monetary_components`, `handle_cascade`, `rebalance_account_task` |
| `synchronous_candidate` | 0 | — |
| `celery_compatibility` | 0 | — |

**Note on the empty `synchronous_candidate` row:** the three
`requires_analysis` tasks are *already* synchronous at their call sites. They are
not candidates to *become* synchronous — they are candidates to have their
misleading task decorators either removed or actually used. Classifying them
`synchronous_candidate` would imply a change that is already the status quo, so
the analysis label is the honest one.

---

## 6. Dispatch-mechanism summary

**verified**:

| Mechanism | Count | Sites |
| --- | --- | --- |
| `.delay(` | 5 | `report_upload.py:147`, `totp.py:102`, `totp.py:139`, `resource_category.py:140`, `test_file_upload_api.py:177` (test) |
| `.apply_async(` | 0 | — |
| `send_task(` | 0 | — |
| `AsyncResult` | 0 | — |
| `add_periodic_task` | 2 | `tasks/__init__.py:13`, `tasks/__init__.py:20` |
| `crontab` | 1 | `tasks/__init__.py:14` |
| Synchronous calls to `@task`-decorated functions | 17 (16 non-test) | §3.6, §3.7, §3.8 |

Breakdown of the 16 non-test synchronous calls:
`rebalance_account_task` 12, `summarise_monetary_components` 2
(`resource_category.py:91`, `viewsets/resource_category.py:208`),
`handle_cascade` 2 (`location.py:128`, `location.py:167`).

**verified** In non-test production code, asynchronous dispatch happens at
exactly **4 call sites**. Synchronous invocation of task-decorated functions
happens at **16** — four times as often.

**inferred** The practical migration surface for Cloud Tasks is therefore much
smaller than the count of `@shared_task` decorators suggests: 4 dispatch sites
across 4 distinct tasks, plus 2 scheduled jobs.
