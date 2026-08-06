---
title: Cache and Redis Inventory
document: inventory/cache-and-redis
version: 0.1.0
status: Draft
phase: 0
source_repository: https://github.com/ohcnetwork/care
source_branch: gcp
source_commit: 6a2976dc2512c2c532fcc70628c5690fbbbe3f3d
reviewed: 2026-08-05
---

# Cache and Redis Inventory

Every cache and Redis use in the repository, classified by role, with a
backend-suitability assessment grounded in the semantics each site actually
requires. No cache or Redis code was modified in this phase.

Evidence labels: **verified** / **inferred** / **unknown**.

---

## 1. Summary

**verified** Redis is used for **four structurally different things**, only one of
which is an ordinary cache:

1. Celery broker and result backend (`base.py:421`, `:423`)
2. Django cache backend (`base.py:85-95`)
3. **Distributed locking via `SETNX`** (`care/utils/lock.py`)
4. **Redis LIST data structures via a raw client** (`care/emr/models/valueset.py`)

**verified** Three distinct hard couplings prevent swapping the cache backend:

| # | Coupling | Location | Why it blocks |
| --- | --- | --- | --- |
| A | `cache.set(..., nx=True)` | `care/utils/lock.py:18`, `:44` | `nx` is not in Django's cache API |
| B | `cache.delete_pattern(...)` | `care/emr/resources/base.py:313`, `:315` | `delete_pattern` is a `django_redis` extension |
| C | `get_redis_connection("default")` | `care/emr/models/valueset.py:77` | raw Redis client, LIST commands |

**verified** These are not stylistic. Each one calls an API that does not exist on
`django.core.cache.backends.db.DatabaseCache` or `LocMemCache`.

---

## 2. Configuration

**verified** `config/settings/base.py`:

```python
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379")   # line 80

CACHES = {                                                        # lines 85-100
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",               # line 87
        "LOCATION": REDIS_URL,                                    # line 88
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",  # line 90
            "IGNORE_EXCEPTIONS": True,                            # line 93
        },
    },
    "swagger_cache": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",  # line 97
        "LOCATION": "swagger-schema-cache",                          # line 98
    },
}
```

**verified** `IGNORE_EXCEPTIONS: True` (`base.py:93`) makes every cache operation
swallow connection errors and return `None`.

**verified interaction with locking:** `Lock.acquire` (`care/utils/lock.py:17-19`)
treats a falsy return from `cache.set` as "lock already held" and raises
`ObjectLocked`. With `IGNORE_EXCEPTIONS: True`, a Redis outage makes `cache.set`
return `None`, so **every lock acquisition fails closed** and every locked
endpoint returns HTTP 423. **inferred** This means Redis is not merely a
performance dependency for those endpoints — it is a hard availability
dependency.

**verified** `config/settings/test.py:44-50` overrides the default cache but still
uses `django_redis.cache.RedisCache` against `REDIS_URL` (`test.py:45-46`). The
test suite therefore requires a live Redis.

**verified** `config/settings/test.py:58` silences `django_ratelimit.E003` and
`W001`.

**verified** `LOCK_TIMEOUT = env.int("LOCK_TIMEOUT", default=32)` at
`config/settings/base.py:78`, commented `# timeout for setnx lock`.

---

## 3. The `nx` shim and what it hides

**verified** `config/caches.py` in full:

```python
from django.core.cache.backends import dummy, locmem
from django.core.cache.backends.base import DEFAULT_TIMEOUT


class DummyCache(dummy.DummyCache):
    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None, nx=None):
        super().set(key, value, timeout, version)
        # mimic the behavior of django_redis with setnx, for tests
        return True                                            # line 9


class LocMemCache(locmem.LocMemCache):
    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None, nx=None):
        super().set(key, value, timeout, version)
        # mimic the behavior of django_redis with setnx, for tests
        return True                                            # line 16
```

**verified** Both subclasses accept `nx` and **ignore it**, unconditionally
returning `True` (`caches.py:9`, `caches.py:16`).

**verified consequence:** under either shimmed backend, `Lock.acquire`
(`lock.py:17-19`) never raises, because `cache.set` always returns truthy.
**Mutual exclusion is silently disabled.** The comment calls this "mimic the
behavior of django_redis with setnx", but it does not mimic `SETNX` — it mimics
only the success case.

**inferred** This is the central risk in "make Redis optional". A naive swap to
`DatabaseCache` or `LocMemCache` does not degrade locking gracefully; it removes
locking while leaving the call sites looking correct. Any PostgreSQL-backed lock
must be a real conditional insert (`INSERT ... ON CONFLICT DO NOTHING`, or
`pg_try_advisory_lock`), not a cache `set`.

**verified** `config/caches.py` is referenced **exactly once**, and only from a
test: `care/utils/tests/test_utils.py:18` sets
`"BACKEND": "config.caches.LocMemCache"` in an override. No settings module —
`base.py`, `local.py`, `test.py`, `deployment.py`, `production.py`,
`staging.py` — points at either class.

**inferred** So the shim exists solely to let one test run without Redis, and the
locking semantics it fakes are never exercised in production. It should be read as
evidence that a LocMem fallback was attempted and left incomplete, not as an
existing non-Redis path.

---

## 4. Call-site classification

Roles use the permitted vocabulary: `celery_broker`, `celery_result_backend`,
`performance_cache`, `shared_cache`, `report_progress`, `rate_limit`,
`distributed_lock`, `transient_state`, `session`, `health_check`, `direct_redis`,
`unknown`.

Backend options: `PostgreSQL database cache`, `explicit PostgreSQL model`,
`LocMem`, `Redis-compatible backend`, `not applicable`.

### 4.1 Broker and result backend

| Site | Line | Role | Viable backend |
| --- | --- | --- | --- |
| `config/settings/base.py` | 421 | `celery_broker` | not applicable — replaced by Cloud Tasks, not re-hosted |
| `config/settings/base.py` | 423 | `celery_result_backend` | not applicable — **no consumer exists**, see `task-call-sites.md` §2 |

**verified** No `AsyncResult` anywhere in the repository. The result backend is
written and never read.

### 4.2 Distributed locking

| Site | Line | Symbol | Role |
| --- | --- | --- | --- |
| `care/utils/lock.py` | 18 | `Lock.acquire` | `distributed_lock` |
| `care/utils/lock.py` | 22 | `Lock.release` | `distributed_lock` |
| `care/utils/lock.py` | 44 | `MultipleItemsLock.acquire` | `distributed_lock` |
| `care/utils/lock.py` | 51 | `MultipleItemsLock.release` | `distributed_lock` |

**verified** `MultipleItemsLock.acquire` (`lock.py:42-47`) acquires keys in list
order and calls `self.release()` on the first failure (`:45`) before raising.

**verified** Locks carry a TTL — `settings.LOCK_TIMEOUT`, default 32 s
(`base.py:78`), applied at `lock.py:18` and `:44`.

**Viable backends:**

- `Redis-compatible backend` — **works today**; this is the status quo.
- `explicit PostgreSQL model` — **viable**, and the only correct PostgreSQL
  option. Requires a unique constraint plus `INSERT ... ON CONFLICT DO NOTHING`
  to get real atomicity, and an explicit expiry column plus a sweeper, since
  PostgreSQL has no native TTL.
- `PostgreSQL database cache` — **not viable as-is.** Django's `DatabaseCache`
  exposes `add()`, which is atomic-ish, but not the `nx=` kwarg these call sites
  pass. `cache.set(..., nx=True)` would raise `TypeError` on `DatabaseCache`.
  Rewriting to `cache.add()` is plausible but changes the return contract and
  needs verification against `DatabaseCache`'s `add()` implementation, which
  performs a `SELECT` then an `INSERT` in a transaction rather than a single
  atomic statement.
- `LocMem` — **not viable.** Per-process memory; provides no mutual exclusion
  across Cloud Run instances. Under the shim it silently always succeeds.

**verified** `care/security/management/commands/sync_permissions_roles.py:14`
documents this dependency in a docstring: *"multiple instances running the same
command is automatically blocked with redis"*.

### 4.3 Raw Redis data structures

| Site | Line | Symbol | Commands | Role |
| --- | --- | --- | --- | --- |
| `care/emr/models/valueset.py` | 77 | `RecentViewsManager.get_client` | `get_redis_connection("default")` | `direct_redis` |
| `care/emr/models/valueset.py` | 83 | `_remove_by_code` | `LRANGE` | `direct_redis` |
| `care/emr/models/valueset.py` | 89 | `_remove_by_code` | `LREM` | `direct_redis` |
| `care/emr/models/valueset.py` | 96 | `get_recent_views` | `LRANGE` | `direct_redis` |
| `care/emr/models/valueset.py` | 109 | `add_recent_view` | `LPUSH` | `direct_redis` |
| `care/emr/models/valueset.py` | 110 | `add_recent_view` | `LTRIM` | `direct_redis` |
| `care/emr/models/valueset.py` | 122 | `clear_recent_views` | `DEL` | `direct_redis` |

**verified** This is a bounded most-recently-used list, capped by
`MAX_RECENT_VIEW` (`valueset.py:72`, default 20) enforced through
`LTRIM(key, 0, MAX-1)` at `:110`.

**verified** `_client` is cached on the class (`valueset.py:71, 76-78`), so the
connection is created once per process.

**Viable backends:**

- `Redis-compatible backend` — works today.
- `explicit PostgreSQL model` — **viable.** A table keyed by user and valueset
  with a timestamp reproduces the semantics: `LPUSH` + `LTRIM` becomes an insert
  plus a delete of rows beyond rank 20; `LREM` by code becomes a delete by code.
  This is a genuine schema addition, not a config change.
- `PostgreSQL database cache` — **not viable.** Django's cache API has no list
  primitives. Emulating with read-modify-write on a JSON blob loses the atomicity
  that `LPUSH`/`LTRIM` provide and would corrupt under concurrency.
- `LocMem` — **not viable.** Per-process; recent views would differ per Cloud Run
  instance.

**verified** `get_redis_connection` is imported from `django_redis` at
`valueset.py:5`. This import fails at module load if `django_redis` is absent, so
it is a hard package dependency, not just a runtime one.

### 4.4 Pattern-based invalidation

| Site | Line | Symbol | Role |
| --- | --- | --- | --- |
| `care/emr/resources/base.py` | 313 | model cache invalidation | `shared_cache` |
| `care/emr/resources/base.py` | 315 | model cache invalidation | `shared_cache` |

**verified** Both lines call `cache.delete_pattern(...)`.

**verified** `delete_pattern` is **not** part of `django.core.cache`. It is a
`django_redis` extension implemented with `SCAN` + `DEL`. Neither
`DatabaseCache` nor `LocMemCache` provides it; calling it raises
`AttributeError`.

**verified** The paired writes are `cache.get` at `base.py:255` and `cache.set` at
`base.py:273`, keyed by `model_cache_key(model_string(db_model), model.__name__, pk)`.

**Viable backends:**

- `Redis-compatible backend` — works today.
- `PostgreSQL database cache` — **viable only after a code change.** `DatabaseCache`
  stores keys in a real table, so a `LIKE`-based delete is expressible, but not
  through the Django cache API. It needs either a custom backend subclass or
  replacing pattern deletion with explicit key enumeration.
- `explicit PostgreSQL model` — not the natural fit; this is genuinely a cache.
- `LocMem` — **not viable** for correctness across instances: stale model data
  would persist on every instance that did not serve the write.

### 4.5 Ordinary performance caches

**verified** These use only `get` / `set` / `delete` / `get_or_set` /
`delete_many` — all portable Django cache API.

| File | Lines | Symbol | Role |
| --- | --- | --- | --- |
| `care/security/models/role.py` | 47, 57, 69, 87, 113, 115 | role permission caching | `performance_cache` |
| `care/emr/models/facility_config.py` | 50, 57, 62, 69, 76, 77 | monetary component / discount config | `performance_cache` |
| `care/emr/models/favorites.py` | 40, 44 | favorites | `performance_cache` |
| `care/emr/api/viewsets/favorites.py` | 40, 55, 102, 105 | favorites list | `shared_cache` |
| `care/emr/resources/favorites/filters.py` | 54, 68 | favorites filter | `performance_cache` |
| `care/emr/api/viewsets/valueset.py` | 124, 133, 155, 176, 193 | valueset favorites | `shared_cache` |
| `care/utils/models/base.py` | 51, 56, 74, 84 | flags cache (`get_or_set`) | `performance_cache` |
| `care/emr/fhir/resources/base.py` | 34, 37 | FHIR lookup, 10 s TTL (`:37`) | `performance_cache` |
| `care/users/api/viewsets/plug_config.py` | 17, 21, 26, 30, 34 | plug config response | `performance_cache` |
| `care/emr/resources/tag/cache_invalidation.py` | 31 | `delete_many` | `shared_cache` |

**Viable backends for this group:**

- `Redis-compatible backend` — works today.
- `PostgreSQL database cache` — **viable.** All operations are within the standard
  Django cache API. Cost is a DB round trip per lookup and a `cache_table` that
  needs `createcachetable` plus periodic culling.
- `LocMem` — **viable only for read-mostly, tolerant-of-staleness entries.** Not
  viable for the `shared_cache` rows, where one instance's invalidation must be
  seen by others. `care/emr/api/viewsets/favorites.py:102-105` and
  `care/emr/resources/tag/cache_invalidation.py:31` delete keys after a write;
  under LocMem, other instances keep serving stale data.

**verified** `care/emr/resources/base.py:255, 273` belongs to this group in API
usage but is invalidated by §4.4's `delete_pattern`, so it inherits that blocker.

### 4.6 Token invalidation

| File | Line | Symbol | Role |
| --- | --- | --- | --- |
| `config/authentication.py` | 21 | `cache.get(ACCESS_TOKEN_INVALIDATION_PREFIX + ...)` | `transient_state` |
| `config/auth_views.py` | 99 | `cache.get(REFRESH_TOKEN_INVALIDATION_PREFIX + ...)` | `transient_state` |
| `config/auth_views.py` | 194, 199 | `cache.set(...)` | `transient_state` |

**verified** This is a JWT denylist: tokens are checked against the cache on every
authenticated request (`authentication.py:21`).

**Viable backends:**

- `Redis-compatible backend` — works today.
- `PostgreSQL database cache` — **viable, with a caveat.** Correctness is fine,
  but `authentication.py:21` runs on **every authenticated request**, so this
  turns into an extra DB query per request. **inferred** measurable latency cost
  on Cloud Run; worth benchmarking before committing.
- `explicit PostgreSQL model` — viable, and would allow indexing and a cleanup job.
- `LocMem` — **not viable.** A token revoked on one instance would remain valid on
  every other instance. This is a security property, not a performance one.

**verified** With `IGNORE_EXCEPTIONS: True` (`base.py:93`), a Redis outage makes
`cache.get` return `None` at `authentication.py:21`, which reads as
"not invalidated" — revoked tokens are accepted. Recorded in
`unresolved-items.md` §4.

### 4.7 Report progress

| File | Line | Symbol | Role |
| --- | --- | --- | --- |
| `care/emr/reports/report_utils.py` | 29 | `set_lock` → `cache.set(cache_key, progress, timeout)` | `report_progress` |
| `care/emr/reports/report_utils.py` | 34 | `get_progress` → `cache.get(cache_key)` | `report_progress` |
| `care/emr/reports/report_utils.py` | 39 | `clear_lock` → `cache.delete(cache_key)` | `report_progress` |

**verified** Despite the `_lock` naming, these do **not** use `nx`. They store an
integer progress percentage under the key
`f"report_generation_lock:{key}"` (`report_utils.py:28, 33, 38`), written at
`report_generation.py:35` (10) and `:46` (30), and cleared in a `finally` block
at `:78`.

**verified** Default TTL is `LOCK_DURATION = 2 * 60` = 120 s
(`report_utils.py:20`), independent of `settings.LOCK_TIMEOUT`.

**verified** Read back by the API at
`care/emr/api/viewsets/report/report_upload.py:140-145`, which returns HTTP 409
with the current progress rather than starting a second generation.

**verified** Because this is a plain `set` and not an `nx` guard, two concurrent
requests can both pass the 409 check before either writes progress. The
"lock" is advisory only.

**Viable backends:**

- `Redis-compatible backend` — works today.
- `PostgreSQL database cache` — **viable.** Plain get/set/delete.
- `explicit PostgreSQL model` — **viable and arguably better**, since the progress
  belongs to a `ReportUpload` row that already exists.
- `LocMem` — **not viable.** The writer is a Celery worker and the reader is an
  API process. They are different processes and, on Cloud Run, different
  containers.

**inferred** This is the clearest example of state that must be shared across the
API/worker boundary. Under Cloud Tasks, the writer becomes a separate Cloud Run
request, so the requirement stands unchanged.

### 4.8 Rate limiting

| File | Line | Symbol | Role |
| --- | --- | --- | --- |
| `config/ratelimit.py` | 3 | `from django_ratelimit.core import is_ratelimited` | `rate_limit` |
| `config/ratelimit.py` | 8-9 | `get_ratelimit_key` — returns the constant `"ratelimit"` | `rate_limit` |
| `config/ratelimit.py` | 47 | `is_ratelimited(...)` | `rate_limit` |
| `config/auth_views.py` | 54 | login rate limit | `rate_limit` |
| `care/emr/utils/mfa.py` | 37, 43 | MFA login, by IP and by user | `rate_limit` |
| `care/users/reset_password_views.py` | 60, 114, 169 | password reset, `10/h` | `rate_limit` |

**verified** `django_ratelimit` is in `INSTALLED_APPS` at
`config/settings/base.py:126`, pinned `==4.1.0` in `Pipfile`.

**verified** `django_ratelimit` uses the Django cache API. It does **not** require
Redis specifically — but its counter increments are only atomic if the backend
implements atomic `incr`.

**Viable backends:**

- `Redis-compatible backend` — works today, atomic `INCR`.
- `PostgreSQL database cache` — **viable but weaker.** `DatabaseCache.incr` is not
  atomic against concurrent writers in the way Redis `INCR` is; limits can be
  overshot under concurrency. **inferred** acceptable for
  password-reset throttling, questionable for security-sensitive MFA limits at
  `care/emr/utils/mfa.py:37, 43`.
- `LocMem` — **not viable.** Per-instance counters mean the effective limit is
  multiplied by the instance count. On autoscaling Cloud Run this defeats the
  control entirely.

**verified** `config/settings/test.py:58` silences `django_ratelimit.E003`, the
system check that warns when the cache backend is unsuitable for rate limiting.

### 4.9 Health checks

| File | Line | Symbol | Role |
| --- | --- | --- | --- |
| `config/settings/base.py` | 457 | `DjangoCacheHealthCheck("Cache", ..., connection_name="default")` | `health_check` |
| `config/settings/base.py` | 458-466 | `DjangoCeleryQueueLengthHealthCheck(..., broker=REDIS_URL, ...)` | `health_check` + `direct_redis` |

**verified** `DjangoCeleryQueueLengthHealthCheck` is constructed with
`broker=REDIS_URL` (`base.py:461`) and `queue_name="celery"` (`:462`). It connects
to Redis directly to measure queue depth.

**verified** Thresholds: `info_length=50` (`:463`), `warning_length=0` (`:464`,
commented "this skips the 300 status code"), `alert_length=200` (`:465`).

**inferred** Under Cloud Tasks this check has no meaning — there is no Redis queue
to measure. It must be removed or replaced with a Cloud Tasks queue-depth probe,
otherwise the health endpoint reports unhealthy in the target runtime.

### 4.10 Sessions

**verified** `django.contrib.sessions` is in `INSTALLED_APPS`
(`config/settings/base.py:114`).

**unknown** No `SESSION_ENGINE` setting appears in `base.py`. **inferred** Django's
default is `django.contrib.sessions.backends.db`, which stores sessions in
PostgreSQL, not Redis. Sessions are therefore **not** a Redis dependency.
Recorded as low-confidence in `unresolved-items.md` §8.

### 4.11 Not cache uses — name collisions

**verified** The following matched a `cache.` grep but are **local variables**, not
the Django cache. Listed so they are not mistaken for cache call sites:

| File | Lines |
| --- | --- |
| `care/security/authorization/token.py` | 104, 105, 143, 144 |
| `care/security/authorization/scheduling.py` | 57, 58, 96, 97 |
| `care/security/authorization/booking.py` | 54, 55, 114, 115 |
| `care/emr/models/questionnaire.py` | 114, 115, 138, 139 |

**verified** In each case `cache` is a local list built with `.extend(...)` and
`.append(...)` from `organization__parent_cache`. There is no `django.core.cache`
import in these files.

**verified** `care/facility/models/facility.py` is a special case: it **does**
import the Django cache at line 4, but never calls it. At line 226 it binds a
local `cache = []` inside `sync_cache`, shadowing the import. The import is dead
and the name collides. Not a cache call site.

---

## 5. Roll-up by role

| Role | Sites | Redis strictly required? |
| --- | --- | --- |
| `celery_broker` | 1 | replaced by Cloud Tasks |
| `celery_result_backend` | 1 | **no** — no consumer exists |
| `distributed_lock` | 4 | **yes**, unless replaced by an explicit PostgreSQL mechanism |
| `direct_redis` | 7 | **yes**, unless replaced by an explicit PostgreSQL model |
| `shared_cache` | 12 | no — PostgreSQL viable; `delete_pattern` needs rework |
| `performance_cache` | 27 | no — PostgreSQL or LocMem viable |
| `transient_state` | 4 | no — PostgreSQL viable; LocMem unsafe |
| `report_progress` | 3 | no — PostgreSQL viable; LocMem unsafe |
| `rate_limit` | 6 invocations + 3 definition lines in `config/ratelimit.py` | no — PostgreSQL viable but weaker; LocMem unsafe |
| `health_check` | 2 | one is Redis-specific and must be replaced |
| `session` | 0 | **no** — DB-backed by default (inferred) |

**verified** Non-test call-site totals, counted mechanically:

| Category | Count | How counted |
| --- | --- | --- |
| Django cache API calls (`get`/`set`/`delete`/`add`/`get_or_set`/`delete_many`/`delete_pattern`/`clear`/`incr`) | **52** | grep over `care/` and `config/`, excluding tests and the §4.11 name collisions |
| Raw Redis client operations | **7** | `care/emr/models/valueset.py` §4.3 |
| `ratelimit(...)` invocations | **6** | `auth_views.py:54`; `mfa.py:37, 43`; `reset_password_views.py:60, 114, 169` |
| Redis-dependent settings entries | **4** | `base.py:421, 423, 457, 458-466` |
| **Total** | **69** | |

Per-file breakdown of the 52 Django cache API calls:

```
6  care/security/models/role.py            4  care/utils/lock.py
6  care/emr/models/facility_config.py      4  care/emr/resources/base.py
5  care/users/api/viewsets/plug_config.py  4  care/emr/api/viewsets/favorites.py
5  care/emr/api/viewsets/valueset.py       3  config/auth_views.py
4  care/utils/models/base.py               3  care/emr/reports/report_utils.py
2  care/emr/resources/favorites/filters.py 2  care/emr/models/favorites.py
2  care/emr/fhir/resources/base.py         1  config/authentication.py
1  care/emr/resources/tag/cache_invalidation.py
```

Test-file cache calls are excluded and listed in §6.

---

## 6. Test-only cache sites

**verified** — excluded from the 67:

| File | Lines |
| --- | --- |
| `care/utils/tests/base.py` | 59, 79, 80 |
| `care/emr/tests/test_favorites_api.py` | 21, 22, 52, 53, 89, 110, 153, 169, 182, 227, 233, 243, 251 |
| `care/emr/tests/test_valueset_api.py` | 23, 52, 462 |
| `care/emr/tests/test_reset_password_api.py` | 24 |

---

## 7. Assessment against the "keep Redis optional" goal

**verified blockers**, in the order they must be resolved:

1. `care/utils/lock.py:18, 44` — `nx=True`. Needs a real PostgreSQL locking
   primitive. **The shim in `config/caches.py` is not one**; it disables locking.
2. `care/emr/resources/base.py:313, 315` — `delete_pattern`. Needs explicit key
   tracking or a custom backend.
3. `care/emr/models/valueset.py:77-122` — raw Redis LIST operations. Needs a
   schema addition.
4. `config/settings/base.py:458-466` — Redis-broker health check. Needs removal
   or replacement.
5. `config/settings/test.py:45-46` — the test suite itself points at Redis. Making
   Redis optional in production without addressing this leaves tests unable to
   exercise the PostgreSQL path.

**inferred** Items 1 and 3 are schema/design work, not configuration. Item 2 is a
contained refactor. Items 4 and 5 are configuration. The claim "Redis is optional"
is not supportable until at least 1, 2 and 3 are done — and item 1 is a
correctness hazard that fails silently rather than loudly.
