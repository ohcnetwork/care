---
title: GCP Implementation Plan
document: 03-migration-plan
version: 0.2.0
status: Draft
source_repository: https://github.com/ohcnetwork/care
target_platform: Google Cloud Platform
deployment_type: Greenfield
depends_on:
  - docs/xii/architecture/00-scope-and-goals.md
  - docs/xii/architecture/01-current-runtime.md
  - docs/xii/architecture/02-target-runtime.md
---

# GCP Implementation Plan

## 1. Purpose

This document defines the implementation sequence required to prepare CARE for
a new deployment on Google Cloud Platform.

This is a greenfield deployment.

There is no existing production installation to migrate.

There are no existing production:

- databases;
- users;
- patient records;
- uploaded files;
- object-storage buckets;
- Redis instances;
- Celery workers;
- virtual machines;
- scheduled jobs;
- production frontend integrations.

The plan therefore focuses on adapting the CARE codebase and creating a new GCP
environment.

It does not include:

- production data migration;
- database replication;
- object copying;
- storage-provider cutover;
- synchronization between old and new systems;
- dual writes;
- compatibility windows for active users;
- rollback to an existing production installation.

The implementation SHALL preserve compatibility with the official CARE
repository and its local development environment.

---

## 2. Objectives

The implementation SHALL produce a new CARE deployment using:

- Cloud Run for the API;
- Cloud SQL for PostgreSQL;
- Cloud Storage through Django Storage API and `django-storages`;
- Cloud Tasks for the default GCP asynchronous task backend;
- a private Cloud Run service for Cloud Tasks execution;
- Cloud Scheduler for periodic triggers;
- Cloud Run Jobs for migrations, setup and batch work;
- PostgreSQL as an option for shared cache, rate limiting, transient state and
  an optional task queue;
- Redis-compatible services as optional backends;
- Secret Manager for secrets;
- Artifact Registry for container images;
- Terraform for GCP infrastructure;
- an automated deployment pipeline.

The default GCP deployment SHALL NOT require:

- Compute Engine;
- a permanently running VM;
- self-managed MinIO;
- self-managed Redis;
- a permanent Celery worker;
- Celery Beat;
- direct frontend access to object storage;
- `boto3` for CARE file storage.

---

## 3. Greenfield Assumptions

The following assumptions apply throughout this plan.

### 3.1 Empty production database

The first production database will be created from CARE migrations.

No previous schema or data must be imported.

### 3.2 Empty production buckets

Cloud Storage buckets will initially contain no CARE files.

No MinIO, S3 or legacy object data must be copied.

### 3.3 No legacy frontend deployment

The production frontend can be deployed using the new API file flow from its
first release.

There is no need to support signed-upload and server-mediated upload flows
simultaneously in production.

### 3.4 No existing task infrastructure

Cloud Tasks, Cloud Scheduler and Cloud Run Jobs can be introduced directly.

There is no production Celery queue or Beat schedule to drain or disable.

### 3.5 Local compatibility remains required

The existing Docker Compose development model SHALL remain functional.

Local CARE development MAY continue using:

- PostgreSQL;
- Redis;
- Celery;
- Celery Beat;
- MinIO.

Greenfield production does not mean local upstream behavior may be broken.

---

## 4. Implementation Principles

### 4.1 Build the desired runtime directly

Production SHALL be created using the target architecture.

The implementation SHALL not first deploy the legacy architecture and then
migrate it.

### 4.2 Preserve upstream compatibility

Changes to upstream-owned files SHALL remain:

- small;
- focused;
- tested;
- easy to merge;
- easy to understand.

Adding isolated settings, scripts and modules is preferred over modifying
shared files extensively.

### 4.3 Use Django facilities first

The implementation SHALL prefer established Django mechanisms.

Examples:

- Django ORM for persistence;
- Django Storage API for files;
- Django cache framework for cache selection;
- Django management commands for administrative and scheduled work;
- Django settings modules for deployment-specific configuration.

### 4.4 Avoid unnecessary abstraction

An abstraction SHALL be introduced only when multiple implementations are
actually supported.

Examples:

- Celery and Cloud Tasks;
- PostgreSQL cache and Redis cache;
- MinIO/S3 and GCS through Django Storage;
- optional PostgreSQL task queue.

The implementation SHALL not introduce domain repositories or reorganize CARE
into new architectural layers.

### 4.5 Keep every phase usable

Each phase SHALL leave:

- the repository buildable;
- tests runnable;
- local development functional;
- completed GCP components testable.

---

## 5. Branch Strategy

The recommended branches are:

```text
upstream/develop
      |
      v
origin/develop
      |
      v
origin/gcp
      |
      v
feature/*
```

### 5.1 `origin/develop`

`origin/develop` SHALL mirror `upstream/develop`.

It SHALL not contain GCP-specific commits.

### 5.2 `origin/gcp`

`origin/gcp` SHALL contain the maintained GCP integration.

It SHOULD remain deployable after each completed phase.

### 5.3 Feature branches

Each major phase SHOULD use a feature branch.

Examples:

```text
feature/gcp-settings
feature/gcp-container
feature/django-storages
feature/file-api
feature/cloud-tasks
feature/postgres-cache
feature/gcp-terraform
```

### 5.4 Upstream synchronization

Official updates SHOULD be integrated through:

```text
sync/upstream-YYYY-MM-DD
```

---

## 6. Commit Strategy

Commits SHALL be small and focused.

Recommended examples:

```text
docs(gcp): document greenfield implementation plan
chore(gcp): add isolated GCP settings
chore(runtime): add production Cloud Run entrypoint
chore(storage): add django-storages dependencies
feat(storage): configure patient facility and report aliases
refactor(storage): save uploads through Django Storage API
refactor(storage): stream downloads through Django
feat(tasks): add task backend selection
feat(tasks): add Cloud Tasks dispatcher
feat(tasks): add authenticated Cloud Run worker endpoint
feat(cache): add PostgreSQL database cache
chore(gcp): add Terraform foundation
test(gcp): add Cloud Run smoke tests
```

Avoid large commits such as:

```text
migrate CARE to GCP
complete cloud refactor
replace infrastructure
```

---

## 7. Phase Overview

The greenfield implementation SHALL proceed through these phases:

```text
Phase 0   Complete repository inventory
Phase 1   Establish test and branch baseline
Phase 2   Add isolated GCP settings
Phase 3   Build the production container
Phase 4   Create Terraform foundation
Phase 5   Deploy Cloud SQL and initialize CARE
Phase 6   Replace CARE file handling with django-storages
Phase 7   Implement server-mediated uploads and downloads
Phase 8   Implement configurable task execution
Phase 9   Add Cloud Tasks and the private worker
Phase 10  Add Cloud Scheduler and Cloud Run Jobs
Phase 11  Add PostgreSQL-backed cache and shared state
Phase 12  Add optional Redis-compatible backends
Phase 13  Evaluate the optional PostgreSQL task queue
Phase 14  Add health checks and observability
Phase 15  Add CI/CD and deployment automation
Phase 16  Verify the complete greenfield deployment
Phase 17  Validate upstream synchronization
```

No production-data migration phase is required.

---

# Phase 0 — Complete Repository Inventory

## 8. Objective

Complete the technical inspection before changing CARE behavior.

The existing `01-current-runtime.md` provides the initial runtime inventory, but
implementation requires a complete call-site inventory.

## 9. Required searches

Locate and document:

- every `.delay()` call;
- every `.apply_async()` call;
- every `send_task()` call;
- every use of Celery result IDs;
- every use of the default Django cache;
- every `django_ratelimit` decorator;
- every direct Redis import;
- every use of `files_manager`;
- every signed-upload endpoint;
- every signed-download endpoint;
- every direct `boto3` or `botocore` import;
- every frontend upload call;
- every frontend download call;
- every periodic Celery registration;
- relevant plugin-provided behavior;
- production Dockerfiles and scripts;
- health-check routes;
- current CI workflows.

## 10. Inventory documents

Store the results under:

```text
docs/xii/architecture/inventory/
```

Recommended files:

```text
storage-call-sites.md
task-call-sites.md
cache-and-redis.md
frontend-file-flow.md
runtime-and-deployment.md
plugin-impact.md
```

## 11. Exit criteria

Phase 0 is complete when:

- all known storage call sites are listed;
- all known task call sites are listed;
- all Redis and cache responsibilities are classified;
- frontend file flows are understood;
- unresolved plugin behavior is documented;
- no application behavior has changed.

---

# Phase 1 — Test and Branch Baseline

## 12. Objective

Establish a reproducible starting point.

## 13. Local baseline

Run the current upstream-compatible workflow:

```bash
make build
make up
make load-fixtures
make test
```

or the current official equivalents.

Record:

- test count;
- failures;
- skipped tests;
- lint result;
- migration status;
- container health;
- fixture-loading result.

Existing failures SHALL be documented.

## 14. Branch setup

Configure:

```text
origin
upstream
```

Example:

```bash
git remote add upstream https://github.com/ohcnetwork/care.git
git fetch upstream
```

Ensure:

```text
origin/develop
```

matches:

```text
upstream/develop
```

Create or update:

```text
origin/gcp
```

from the upstream mirror.

## 15. Exit criteria

Phase 1 is complete when:

- the local stack starts;
- the baseline is documented;
- branch roles are established;
- `develop` mirrors upstream;
- `gcp` is ready for implementation.

---

# Phase 2 — Isolated GCP Settings

## 16. Objective

Add a GCP deployment profile without rewriting existing settings.

## 17. New module

Create:

```text
config/settings/gcp.py
```

It SHALL inherit from:

```python
from .deployment import *
```

## 18. Initial responsibilities

The module SHALL configure:

- Cloud Run proxy behavior;
- secure host and origin handling;
- Cloud SQL connection values;
- task backend selection;
- cache backend selection;
- Redis optionality;
- backend-aware health checks;
- stdout and stderr logging;
- file-size limits;
- GCP storage aliases when Phase 6 is implemented.

## 19. Required configuration

Production SHALL require explicit values for sensitive settings such as:

```text
DJANGO_SECRET_KEY
DATABASE_URL
CSRF_TRUSTED_ORIGINS
CORS_ALLOWED_ORIGINS
```

Unsafe development defaults SHALL not silently apply.

## 20. Backend-selection variables

The settings SHOULD recognize:

```text
CARE_TASK_BACKEND=cloud_tasks|postgres|celery
CARE_CACHE_BACKEND=postgres|locmem|redis|dummy
CARE_RATE_LIMIT_BACKEND=postgres|redis
CARE_TRANSIENT_STATE_BACKEND=postgres|redis
```

Only implemented and tested combinations SHALL be accepted.

Unsupported values SHALL cause a clear configuration error.

## 21. Exit criteria

Phase 2 is complete when:

```bash
DJANGO_SETTINGS_MODULE=config.settings.deployment \
python manage.py check
```

passes with a minimal valid environment.

Local, test and deployment settings SHALL continue working.

---

# Phase 3 — Production Container

## 22. Objective

Produce one immutable image usable by API, workers and jobs.

## 23. Dockerfile

Reuse an existing production Dockerfile when suitable.

Otherwise add:

```text
docker/gcp.Dockerfile
```

## 24. Image requirements

The image SHALL:

- install locked dependencies;
- install required GCP packages;
- install `django-storages` backends;
- compile translations;
- collect static files;
- use Gunicorn;
- avoid development tooling;
- run as non-root where practical;
- avoid embedded secrets;
- support multiple commands;
- avoid running migrations automatically.

## 25. Runtime commands

The image SHOULD support:

```text
API
Cloud Tasks HTTP worker
optional PostgreSQL queue worker
Celery worker
Django management commands
```

Suggested scripts:

```text
scripts/start-gcp-api.sh
scripts/start-gcp-task-worker.sh
scripts/start-postgres-queue-worker.sh
scripts/run-gcp-job.sh
```

## 26. API command

The API SHALL listen on Cloud Run's `PORT`.

Conceptually:

```bash
gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${GUNICORN_WORKERS}" \
  --threads "${GUNICORN_THREADS}" \
  --timeout "${GUNICORN_TIMEOUT}"
```

## 27. Exit criteria

Phase 3 is complete when:

- the production image builds;
- the API starts locally with Gunicorn;
- static files are present;
- the image executes management commands;
- the image does not require Redis unless selected;
- the development Dockerfile remains functional.

---

# Phase 4 — Terraform Foundation

## 28. Objective

Create the GCP environment reproducibly before application deployment.

## 29. Terraform layout

Recommended structure:

```text
deploy/gcp/terraform/
├── modules/
├── environments/
│   ├── dev/
│   ├── staging/
│   └── prod/
└── README.md
```

The initial implementation MAY begin with `dev` only.

## 30. Initial resources

Terraform SHALL create:

- required GCP APIs;
- Artifact Registry;
- Cloud SQL;
- Cloud Storage buckets;
- Secret Manager resources;
- service accounts;
- IAM bindings;
- Cloud Run API service definition;
- Cloud Run task-worker definition;
- Cloud Run Job definitions;
- Cloud Tasks queues;
- Cloud Scheduler jobs;
- required networking;
- logging and monitoring foundations.

Resources MAY be introduced incrementally as their application phase is
completed.

## 31. Environments

Because this is greenfield, environments can be created directly using the
target architecture.

Suggested environments:

```text
dev
staging
prod
```

Each SHOULD have separate:

- database;
- buckets;
- queues;
- services;
- secrets;
- scheduled jobs.

## 32. Exit criteria

Phase 4 is complete when:

- Terraform initializes;
- Terraform validates;
- a development plan can be reviewed;
- Artifact Registry exists;
- state storage is secured;
- IAM ownership is documented.

---

# Phase 5 — Cloud SQL and Initial CARE Database

## 33. Objective

Create a new CARE database directly from Django migrations.

## 34. Cloud SQL creation

Create a development Cloud SQL PostgreSQL instance with:

- a CARE database;
- a dedicated application user;
- backups;
- conservative sizing;
- controlled access;
- connection monitoring.

No legacy database import is required.

## 35. Migration job

Create a Cloud Run Job using the same application image.

The initial database SHALL be created by running:

```bash
python manage.py migrate --noinput
```

## 36. Initial setup

Run required setup commands explicitly:

```bash
python manage.py sync_permissions_roles
python manage.py sync_valueset
```

Fixtures MAY be loaded in development or staging:

```bash
python manage.py load_fixtures
```

Production fixture behavior SHALL be intentional and documented.

## 37. Connection budget

Calculate a conservative connection budget from:

```text
API maximum instances
worker maximum instances
Gunicorn processes
Gunicorn threads
jobs
optional queue worker
```

Using PostgreSQL for cache or queues SHALL also be included in capacity
planning.

## 38. Exit criteria

Phase 5 is complete when:

- Cloud SQL is created;
- migrations succeed on an empty database;
- setup commands succeed;
- CARE connects from Cloud Run;
- database health checks pass;
- no legacy data import is needed.

---

# Phase 6 — Django Storage Implementation

## 39. Objective

Replace CARE's custom S3-specific file-management implementation with Django
Storage API before the first production deployment.

Because the deployment is greenfield, no legacy storage compatibility period is
required in production.

## 40. Dependencies

Add `django-storages` with:

```text
S3-compatible backend
Google Cloud Storage backend
```

Update the repository lockfile.

## 41. Logical aliases

Configure:

```text
patient
facility
report
staticfiles
```

### Local configuration

```text
patient  -> S3Storage -> MinIO
facility -> S3Storage -> MinIO
report   -> S3Storage -> MinIO
```

### GCP configuration

```text
patient  -> GoogleCloudStorage
facility -> GoogleCloudStorage
report   -> GoogleCloudStorage
```

The `report` alias MAY use the same physical bucket as `patient` while
remaining logically separate.

## 42. Refactor storage operations

Replace CARE file operations with:

```python
from django.core.files.storage import storages
```

Use Django Storage methods such as:

```text
save
open
exists
delete
size
```

Remove storage-specific URL construction from application logic.

## 43. Existing object names

The current naming convention MAY be retained:

```text
<file_type>/<internal_name>
```

No object migration is required because production buckets are empty.

## 44. Compatibility wrapper

A thin wrapper MAY temporarily preserve existing internal method signatures
during code refactoring.

It SHALL delegate only to Django Storage API.

It SHALL NOT:

- create `boto3` clients;
- create GCS clients;
- generate signed URLs;
- duplicate provider CRUD logic.

The wrapper SHOULD be removed if direct Django Storage use produces a cleaner
and sufficiently small upstream patch.

## 45. Storage tests

Test both:

```text
MinIO through S3Storage
GCS through GoogleCloudStorage
```

Required operations:

- save;
- open;
- streaming read;
- exists;
- delete;
- Unicode names;
- duplicate names;
- content type;
- large file within supported limits;
- missing object;
- permission errors.

## 46. Exit criteria

Phase 6 is complete when:

- local storage works through MinIO and `django-storages`;
- GCP storage works through GCS and `django-storages`;
- CARE storage code no longer calls `boto3`;
- production buckets remain empty until the application is launched;
- no storage-data migration is required.

---

# Phase 7 — Server-Mediated File API

## 47. Objective

Implement the only production file flow before the frontend is deployed.

All uploads and downloads SHALL pass through CARE.

There is no need for a production compatibility window with signed URLs.

## 48. Upload endpoints

The API SHALL:

1. authenticate the caller;
2. authorize the operation;
3. validate metadata;
4. validate extension;
5. validate MIME type;
6. enforce size limits;
7. save through the correct storage alias;
8. create or update the CARE record;
9. return provider-neutral metadata.

## 49. Upload handling

The implementation SHOULD pass Django uploaded-file objects directly to
storage.

It SHALL avoid reading entire files into memory unnecessarily.

Configure:

```text
DATA_UPLOAD_MAX_MEMORY_SIZE
FILE_UPLOAD_MAX_MEMORY_SIZE
```

and a documented maximum upload size.

## 50. Download endpoints

The API SHALL:

1. authenticate the caller;
2. authorize access;
3. open the object through Django Storage;
4. return `FileResponse` or equivalent streaming response;
5. set safe content type;
6. set safe content disposition.

The API SHALL not return normal direct bucket URLs.

## 51. Frontend implementation

The first production frontend SHALL use the new API flow.

It SHALL NOT implement or retain production support for:

- signed PUT URLs;
- direct MinIO uploads;
- direct S3 uploads;
- direct GCS uploads;
- signed storage downloads;
- external bucket endpoints.

## 52. Security tests

Test:

- unauthenticated access;
- unauthorized access;
- patient and facility boundaries;
- filename handling;
- MIME validation;
- extension validation;
- file-size limits;
- streaming behavior;
- missing objects;
- deleted records;
- storage failures.

## 53. Exit criteria

Phase 7 is complete when:

- the backend file API works;
- the frontend uses it;
- no production direct-to-bucket flow exists;
- memory usage is acceptable;
- Cloud Run request duration is acceptable;
- no legacy production frontend must be supported.

---

# Phase 8 — Task Inventory and Reusable Task Logic

## 54. Objective

Prepare current Celery tasks for configurable execution.

## 55. Task analysis

For each task, document:

- call sites;
- arguments;
- result usage;
- duration;
- retries;
- expiry;
- idempotency;
- storage access;
- database effects;
- email effects;
- periodic scheduling;
- plugin ownership.

## 56. Task classification

Classify each task as:

```text
Cloud Tasks
Cloud Run Job
synchronous
Celery compatibility
requires further analysis
```

## 57. Reusable functions

Extract task behavior from Celery decorators only where needed.

Target structure:

```text
reusable implementation
thin Celery wrapper
thin Cloud Tasks handler
optional PostgreSQL queue wrapper
```

Preserve existing task names where practical.

## 58. Dispatch API

Add a narrow API conceptually similar to:

```python
enqueue_task(
    task_name,
    payload,
    delay_seconds=None,
    task_id=None,
)
```

The implementation SHALL not include unused Celery workflow concepts.

## 59. Transaction timing

Use:

```python
transaction.on_commit(...)
```

where task dispatch must occur only after database commit.

## 60. Exit criteria

Phase 8 is complete when:

- all core tasks are classified;
- reusable logic exists where required;
- Celery still works locally;
- task payloads are JSON-serializable;
- callers do not depend on undocumented Celery behavior.

---

# Phase 9 — Cloud Tasks and Private Worker

## 61. Objective

Implement the default GCP asynchronous execution path.

## 62. Cloud Tasks dispatcher

The dispatcher SHALL:

- use the official Google client;
- use Application Default Credentials;
- enqueue HTTP tasks;
- serialize JSON;
- support delays where required;
- attach OIDC identity;
- return the task name;
- avoid logging sensitive payloads.

## 63. Private worker

Deploy a private Cloud Run service with:

```text
minimum instances: 0
allow unauthenticated: false
```

The worker SHALL:

- accept only POST;
- validate payloads;
- allow only registered tasks;
- reject arbitrary callables;
- log task metadata;
- return non-2xx on retriable failure;
- remain idempotent.

## 64. IAM

Use a dedicated task-invoker service account.

It SHALL receive permission to invoke only the worker service.

## 65. Pilot task

Select one bounded, low-risk task that:

- does not require Celery result retrieval;
- has a small payload;
- is easy to observe;
- can tolerate retries;
- can be made idempotent.

Test:

- enqueue;
- scale from zero;
- execution;
- retry;
- duplicate delivery;
- authorization;
- failure logging.

## 66. Remaining tasks

Migrate request-triggered tasks individually.

The default expected mapping is:

| CARE task | GCP execution |
|---|---|
| TOTP enabled email | Cloud Tasks |
| TOTP disabled email | Cloud Tasks |
| report generation | Cloud Tasks, after duration testing |

## 67. Exit criteria

Phase 9 is complete when:

- Cloud Tasks enqueues successfully;
- the worker scales from zero;
- IAM blocks unauthorized callers;
- migrated tasks execute reliably;
- local Celery execution still passes tests.

---

# Phase 10 — Cloud Scheduler and Cloud Run Jobs

## 68. Objective

Implement periodic and administrative work directly in the target GCP model.

There is no production Celery Beat process to transition or drain.

## 69. Management commands

Expose reusable periodic logic as Django management commands.

Expected commands include:

```text
cleanup_expired_token_slots
cleanup_incomplete_file_uploads
```

## 70. Jobs

Create Cloud Run Jobs for:

```text
migrate
sync_permissions_roles
sync_valueset
load_fixtures, in approved environments
cleanup_expired_token_slots
cleanup_incomplete_file_uploads
other batch operations
```

## 71. Scheduler

Create Cloud Scheduler triggers for periodic jobs.

Reproduce the intended CARE schedules:

```text
expired token cleanup: daily
incomplete upload cleanup: according to configured expiry
```

## 72. Idempotency

Jobs SHALL tolerate retries and repeated invocation.

Cleanup jobs SHALL process empty databases and empty buckets successfully.

This is especially important for the initial greenfield deployment, where
scheduled jobs may run before substantial data exists.

## 73. Exit criteria

Phase 10 is complete when:

- migrations run as jobs;
- setup commands run as jobs;
- periodic cleanup runs through Scheduler and Jobs;
- no production Celery Beat is deployed;
- local Celery Beat remains available.

---

# Phase 11 — PostgreSQL Cache and Shared State

## 74. Objective

Support a Redis-free GCP profile using the already required PostgreSQL service.

## 75. Database cache

Add support for:

```text
django.core.cache.backends.db.DatabaseCache
```

Example configuration:

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "care_cache",
    },
}
```

Create the table during initial environment setup:

```bash
python manage.py createcachetable
```

Because the database is new, no cache migration is required.

## 76. Backend selection

Support:

```text
CARE_CACHE_BACKEND=postgres
CARE_CACHE_BACKEND=locmem
CARE_CACHE_BACKEND=redis
CARE_CACHE_BACKEND=dummy
```

## 77. Appropriate PostgreSQL uses

PostgreSQL MAY support:

- shared Django cache;
- report progress;
- shared transient state;
- rate-limit counters;
- task execution state;
- idempotency.

Use explicit models instead of cache tables when state must be:

- durable;
- auditable;
- queryable;
- correctness-critical.

## 78. Report progress

Choose between:

```text
Django database cache
explicit PostgreSQL model
```

A model SHOULD be used when task failures or historical progress must remain
visible.

## 79. Rate limiting

Test the current rate-limiting library with the PostgreSQL-backed cache.

If required atomicity is not guaranteed, implement explicit PostgreSQL
counters using transactions and constraints.

## 80. Capacity testing

Measure:

- cache queries per request;
- rate-limit writes;
- task-progress writes;
- table growth;
- expired-row cleanup;
- database latency;
- connection usage.

## 81. Exit criteria

Phase 11 is complete when:

- the API starts without Redis;
- the worker starts without Redis;
- shared cache works across instances;
- report progress works across instances;
- rate limiting remains correct;
- PostgreSQL load is acceptable.

---

# Phase 12 — Optional Redis-Compatible Backends

## 82. Objective

Allow Redis-compatible services when they provide a measurable benefit.

Redis SHALL remain optional.

## 83. Supported responsibilities

Redis MAY provide:

- cache;
- rate limiting;
- shared transient state;
- Celery broker in traditional deployments;
- Celery result backend.

## 84. Independent configuration

Support variables such as:

```text
REDIS_CACHE_URL
REDIS_RATE_LIMIT_URL
REDIS_TRANSIENT_STATE_URL
```

The variables MAY point to one instance but SHALL remain logically separate.

## 85. Provider neutrality

Use standard Redis-compatible clients and URLs.

An Upstash deployment SHOULD use:

```text
CARE_CACHE_BACKEND=redis
REDIS_CACHE_URL=rediss://...
```

The application SHOULD not require an Upstash-specific switch.

## 86. Failure behavior

Document behavior for each responsibility.

Examples:

```text
performance cache failure -> cache miss
rate-limit failure -> defined security fallback
progress failure -> controlled degradation
Celery broker failure -> dispatch error
```

## 87. Exit criteria

Phase 12 is complete when:

- Redis can be enabled selectively;
- the Redis-free profile still works;
- TLS configuration is tested;
- Upstash-compatible configuration is documented;
- Redis checks run only when required.

---

# Phase 13 — Optional PostgreSQL Task Queue Evaluation

## 88. Objective

Determine whether CARE should support a PostgreSQL-backed task queue in addition
to Cloud Tasks and Celery.

This phase SHALL NOT block the default GCP deployment.

## 89. Evaluation scope

Evaluate a maintained queue system intentionally designed for PostgreSQL.

Do not use an obsolete Celery SQL broker transport.

Required capabilities:

- Django compatibility;
- PostgreSQL-native locking;
- retries;
- scheduled execution;
- concurrency controls;
- task state;
- transactional enqueue;
- schema management;
- cleanup;
- observability.

## 90. Greenfield advantage

Because there is no production queue, the candidate can be tested on an empty
schema without converting Celery messages or preserving queued jobs.

No queue migration is required.

## 91. Worker implications

Document that an immediate PostgreSQL queue needs an active consumer.

Possible modes:

```text
Cloud Run service with minimum instance 1
traditional worker container
Kubernetes or on-premise worker
periodic Cloud Run Job for non-urgent work
```

A PostgreSQL queue SHALL not be described as equivalent to Cloud Tasks for
scale-to-zero behavior.

## 92. Benchmark

Measure:

- enqueue latency;
- claim latency;
- polling or notification behavior;
- database connections;
- table growth;
- retries;
- throughput;
- effect on CARE queries;
- minimum worker cost.

## 93. Decision

Produce an ADR with one of:

```text
accepted
accepted for limited deployment profiles
deferred
rejected
```

## 94. Exit criteria

Phase 13 is complete when the project has a documented decision.

The default Cloud Tasks deployment may be completed regardless of the outcome.

---

# Phase 14 — Health Checks and Observability

## 95. Objective

Make operational behavior reflect the selected runtime profile.

## 96. Health categories

Define:

```text
liveness
readiness
dependency diagnostics
```

The mandatory GCP readiness checks SHALL cover:

- application startup;
- PostgreSQL.

Additional checks SHALL depend on configuration.

Examples:

### Cloud Tasks profile

```text
no Celery queue check
no Redis check unless Redis is enabled
```

### PostgreSQL cache profile

```text
database and cache table availability
```

### Redis profile

```text
Redis only when required by selected responsibilities
```

### PostgreSQL queue profile

```text
queue schema and worker freshness
```

## 97. Structured logging

Include:

```text
service
revision
environment
request ID
task ID
task backend
task name
attempt
duration
status
```

## 98. Sensitive-data review

Logs SHALL not include:

- passwords;
- tokens;
- complete patient records;
- full task payloads;
- file contents;
- storage credentials;
- secret values.

## 99. Initial alerts

Configure alerts for:

- API error rate;
- task failures;
- scheduled-job failures;
- Cloud SQL connections;
- Cloud SQL storage;
- storage-access failures;
- task backlog;
- optional Redis failures.

## 100. Exit criteria

Phase 14 is complete when:

- health checks match the active profile;
- logs are structured;
- sensitive logging is reviewed;
- essential alerts exist.

---

# Phase 15 — CI/CD and Deployment Automation

## 101. Objective

Deploy immutable revisions into an empty or newly initialized environment.

## 102. Pipeline sequence

The pipeline SHALL:

1. run formatting checks;
2. run linting;
3. run tests;
4. build the image;
5. tag the image with the commit SHA;
6. push to Artifact Registry;
7. create or update job definitions;
8. run database migrations;
9. create the database-cache table when selected;
10. run required setup commands;
11. deploy the task worker;
12. deploy the API;
13. create or update scheduled jobs;
14. run smoke tests;
15. record the deployed revision.

## 103. First deployment

The first deployment has no previous production revision.

It SHALL:

- create the empty infrastructure;
- initialize the database;
- initialize cache or queue schemas;
- deploy services;
- verify the complete stack.

## 104. Later application rollback

After the first deployment, application rollback MAY deploy a previous
immutable Cloud Run revision.

Database-schema compatibility SHALL be checked.

There is no rollback to a legacy CARE infrastructure because none exists.

## 105. Exit criteria

Phase 15 is complete when:

- a clean environment can be deployed automatically;
- migrations are explicit;
- services use immutable images;
- smoke tests gate deployment success;
- subsequent revision rollback is documented.

---

# Phase 16 — Complete Greenfield Verification

## 106. Objective

Verify the complete new installation before real use.

## 107. Functional tests

Verify:

- initial administrative access;
- authentication;
- permissions;
- facilities;
- patients;
- encounters;
- file upload;
- file download;
- report generation;
- email tasks;
- periodic cleanup;
- cache;
- rate limiting;
- audit logs;
- relevant plugins.

Use only synthetic test data.

## 108. Scaling tests

Verify:

- API scale from zero;
- worker scale from zero;
- concurrent requests;
- database connection limits;
- storage streaming;
- task retries;
- duplicate task delivery;
- scheduled-job execution.

## 109. Empty-state tests

Because the installation is new, explicitly test:

- empty database screens and APIs;
- empty buckets;
- cleanup jobs with no records;
- report endpoints before templates exist;
- first-user and first-facility workflows;
- fixture and value-set initialization.

## 110. Failure tests

Simulate:

- Cloud SQL interruption;
- GCS permission failure;
- task exception;
- duplicate task request;
- email-provider failure;
- optional Redis outage;
- failed migration in a disposable environment.

## 111. Cost validation

Measure expected cost for:

```text
Cloud SQL
Cloud Run
Cloud Tasks
Cloud Storage
Cloud Scheduler
Artifact Registry
Secret Manager
Cloud Logging
optional Redis
optional active PostgreSQL queue worker
```

## 112. Exit criteria

Phase 16 is complete when:

- functional tests pass;
- empty-state behavior works;
- connection usage is safe;
- storage streaming is acceptable;
- task behavior is reliable;
- expected costs are documented;
- the environment is ready for first real use.

---

# Phase 17 — Upstream Synchronization Validation

## 113. Objective

Prove that the GCP fork remains maintainable.

## 114. Synchronization process

Use:

```bash
git fetch upstream

git switch develop
git reset --hard upstream/develop
git push --force-with-lease origin develop

git switch gcp
git switch -c sync/upstream-YYYY-MM-DD
git merge develop
```

## 115. Validation

After conflict resolution, run:

```bash
make build
make up
make test
```

Also verify:

```text
GCP settings
production image
Django storage aliases
file API
Cloud Tasks dispatch
PostgreSQL cache
Terraform validation
```

## 116. Repeated conflicts

If the same upstream file repeatedly conflicts, move GCP behavior into:

- a separate settings module;
- a helper;
- a new script;
- configuration;
- a narrowly scoped extension point.

## 117. Exit criteria

Phase 17 is complete when:

- a current upstream merge succeeds;
- local tests pass;
- GCP tests pass;
- recurring conflicts are documented;
- the synchronization procedure is reproducible.

---

## 118. Test Matrix

The implementation SHALL test these profiles:

| Profile | Database | Storage | Tasks | Cache |
|---|---|---|---|---|
| Local upstream-compatible | PostgreSQL container | MinIO through `S3Storage` | Celery + Redis | Redis |
| GCP default | Cloud SQL | GCS through `GoogleCloudStorage` | Cloud Tasks | PostgreSQL |
| GCP optional Redis | Cloud SQL | GCS | Cloud Tasks | Redis-compatible |
| Consolidated PostgreSQL | PostgreSQL | configured Django storage | PostgreSQL queue | PostgreSQL |
| Test | test database | temporary test storage | fake/eager backend | Dummy or LocMem |

The consolidated PostgreSQL profile is required only if Phase 13 accepts it.

---

## 119. Simplified Rollback Model

Because the deployment is greenfield, rollback is limited to newly deployed
code and infrastructure.

### Before first production use

The entire environment MAY be recreated from Terraform and initialized again.

No production data preservation is required before real use begins.

### After real use begins

Normal operational protections become necessary:

- Cloud SQL backups;
- point-in-time recovery;
- Cloud Storage retention;
- immutable application revisions;
- migration compatibility.

### Application rollback

Deploy a previous immutable Cloud Run revision.

### Cache backend changes

Cache values are disposable.

Changing among:

```text
postgres
redis
locmem
dummy
```

does not require data migration.

### Task backend changes

Switching task backends requires the selected worker or service to exist.

Because no legacy queue is migrated during initial deployment, there are no
old queued messages to preserve.

### Infrastructure recreation

Development and staging environments SHOULD be reproducible from Terraform.

Production stateful resources SHALL not be destroyed casually after real data
exists.

---

## 120. Implementation Risks

### 120.1 File traffic through Cloud Run

Files pass through Django.

Potential effects:

- request duration;
- memory usage;
- Cloud Run bandwidth;
- maximum file size.

Mitigations:

- streaming;
- Django temporary-file handlers;
- explicit limits;
- adequate CPU and memory;
- realistic tests before first use.

### 120.2 Cloud SQL load

PostgreSQL may support:

- CARE data;
- cache;
- rate limiting;
- progress;
- optional queueing.

The implementation SHALL measure whether consolidation requires a larger
instance.

### 120.3 Task duplication

Cloud Tasks and PostgreSQL queues may retry.

Task handlers SHALL be idempotent before production use.

### 120.4 Frontend file-flow changes

The frontend must implement server-mediated files from its first production
release.

There is no need for a legacy production compatibility flow.

### 120.5 Upstream changes

Storage, settings and task files may change upstream.

Custom patches SHALL remain narrow.

### 120.6 Plugins

Plugins may assume:

- Celery;
- Redis;
- S3 APIs;
- signed URLs.

Required plugins SHALL be tested before first production deployment.

---

## 121. Deliverables

The complete implementation SHALL produce:

```text
config/settings/gcp.py
production container definition
Cloud Run API entrypoint
Cloud Run task-worker entrypoint
Cloud Run Job definitions
Django Storage aliases
server-mediated upload API
server-mediated download API
task dispatcher
Cloud Tasks backend
PostgreSQL cache support
optional Redis support
optional PostgreSQL queue decision
Terraform
deployment pipeline
test suite
operations documentation
upstream synchronization documentation
```

---

## 122. Definition of Completion

The implementation is complete when:

- CARE can be deployed from scratch into a new GCP project;
- no Compute Engine VM is required;
- the API runs on Cloud Run;
- the Cloud Tasks worker runs privately on Cloud Run;
- both services can scale to zero;
- Cloud SQL is initialized directly from Django migrations;
- no production data migration is required;
- Cloud Storage buckets are created empty;
- all file traffic passes through Django;
- `django-storages` handles MinIO and GCS;
- no CARE storage code uses `boto3`;
- Cloud Tasks handles default asynchronous work;
- Scheduler and Jobs handle periodic and administrative work;
- PostgreSQL can provide shared cache and state;
- Redis remains optional;
- the optional PostgreSQL queue has an explicit decision;
- local Docker Compose remains functional;
- the frontend uses the new file API from its first production release;
- the environment passes greenfield acceptance tests;
- upstream synchronization is proven.

---

## 123. Next Document

The next document is:

```text
docs/xii/architecture/04-testing.md
```

It will define:

- unit tests;
- storage integration tests;
- file API tests;
- task-backend tests;
- PostgreSQL cache tests;
- optional PostgreSQL queue tests;
- Redis compatibility tests;
- Cloud Run smoke tests;
- empty-state tests;
- security tests;
- upstream compatibility gates.
