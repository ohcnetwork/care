---
title: GCP Configuration Reference
document: 07-configuration-reference
version: 0.1.0
status: Draft
source_repository: https://github.com/ohcnetwork/care
target_platform: Google Cloud Platform
deployment_type: Greenfield
depends_on:
  - docs/xii/architecture/00-scope-and-goals.md
  - docs/xii/architecture/01-current-runtime.md
  - docs/xii/architecture/02-target-runtime.md
  - docs/xii/architecture/03-migration-plan.md
  - docs/xii/architecture/04-testing.md
  - docs/xii/architecture/05-upstream-sync.md
  - docs/xii/architecture/06-operations.md
---

# GCP Configuration Reference

## 1. Purpose

This document defines the configuration contract for the greenfield CARE
deployment on Google Cloud Platform.

It specifies:

- environment variables;
- supported backend values;
- required and optional settings;
- validation rules;
- safe defaults;
- production restrictions;
- compatibility variables;
- role-specific configuration;
- backend-specific configuration.

This document describes the intended configuration interface.

Exact implementation details MAY differ where required by the current CARE,
Django, `django-storages` or Google Cloud library versions.

Any implementation difference SHALL preserve the behavior described here.

---

## 2. Configuration Principles

CARE configuration SHALL follow these principles.

### 2.1 Environment-based configuration

Deployment configuration SHALL be injected through:

- environment variables;
- Secret Manager references;
- Cloud Run service configuration;
- Cloud Run Job configuration;
- Terraform variables.

Production configuration SHALL NOT be stored in committed `.env` files.

### 2.2 Explicit backend selection

Backend choices SHALL use explicit variables.

Examples:

```text
CARE_TASK_BACKEND=cloud_tasks
CARE_CACHE_BACKEND=postgres
CARE_RATE_LIMIT_BACKEND=postgres
CARE_TRANSIENT_STATE_BACKEND=postgres
```

The application SHALL NOT infer the entire runtime from variables such as:

```text
IS_GCP=true
USE_SERVERLESS=true
PRODUCTION_PROVIDER=google
```

### 2.3 Validate only selected backends

Variables required by an unused backend SHALL not be mandatory.

For example:

```text
REDIS_CACHE_URL
```

SHALL not be required when:

```text
CARE_CACHE_BACKEND=postgres
```

Likewise:

```text
GCP_TASKS_QUEUE
```

SHALL not be required when:

```text
CARE_TASK_BACKEND=celery
```

### 2.4 Fail clearly

Invalid or incomplete production configuration SHALL fail during startup or
deployment validation with a clear error.

Errors SHOULD identify:

- variable name;
- invalid or missing value;
- selected backend;
- supported alternatives.

### 2.5 No secret aliases with insecure defaults

Production secrets SHALL not have usable development defaults.

The GCP settings SHALL not silently use values such as:

```text
secret
changeme
postgres
minioadmin
```

for production credentials.

---

# 3. Configuration Layers

The configuration is divided into these groups:

```text
Django core
application identity
Cloud Run
database
storage
task execution
cache
rate limiting
transient state
optional Redis
email
security
logging and monitoring
service-specific roles
jobs and schedules
```

---

# 4. Settings Module

## 4.1 `DJANGO_SETTINGS_MODULE`

Required for all GCP roles.

```text
DJANGO_SETTINGS_MODULE=config.settings.deployment
```

`config.settings.deployment` is the production settings module the repository
already ships; GCP introduces no settings module of its own. Provider selection
is configuration, not code (ADR-0001), so the same module serves AWS and GCP.

The API, worker and jobs SHOULD all use the same settings module unless a
future role requires a narrowly scoped alternative.

Production SHALL NOT use:

```text
config.settings.local
```

The Celery compatibility runtime MAY use an existing production or
deployment-oriented settings module outside GCP.

---

# 5. Environment Identity

## 5.1 `CARE_ENVIRONMENT`

Required.

Supported values:

```text
dev
staging
prod
```

Example:

```text
CARE_ENVIRONMENT=prod
```

This value SHOULD be included in:

- logs;
- Sentry environment;
- metrics labels;
- deployment annotations;
- task metadata.

Unknown values SHALL be rejected unless explicitly allowed for ephemeral test
environments.

## 5.2 `APP_VERSION`

Recommended.

Example:

```text
APP_VERSION=gcp-v2026.08.05.1
```

This value identifies the logical application release.

## 5.3 `GIT_COMMIT_SHA`

Recommended.

Example:

```text
GIT_COMMIT_SHA=3f49b8a...
```

It SHOULD match the source used to build the deployed image.

## 5.4 `UPSTREAM_COMMIT_SHA`

Recommended.

This records the upstream CARE commit included in the fork.

## 5.5 `DEPLOYED_AT`

Optional.

ISO-8601 timestamp identifying deployment time.

---

# 6. Django Core Configuration

## 6.1 `DJANGO_SECRET_KEY`

Required secret.

Example reference:

```text
projects/<project>/secrets/care-django-secret/versions/<version>
```

It SHALL:

- contain sufficient entropy;
- remain secret;
- differ between environments;
- not use a development default;
- be rotated only through a documented procedure.

## 6.2 `DJANGO_DEBUG`

Production-required value:

```text
DJANGO_DEBUG=false
```

`true` SHALL be prohibited in production.

Development and controlled staging environments MAY enable debugging only when
access is restricted and sensitive data is absent.

## 6.3 `DJANGO_ALLOWED_HOSTS`

Required.

Recommended representation:

```text
DJANGO_ALLOWED_HOSTS=["care-api.example.org",".run.app"]
```

The exact parser MAY accept JSON or comma-separated values according to the
existing CARE environment helper.

A wildcard:

```text
*
```

SHALL not be the normal production value.

## 6.4 `CSRF_TRUSTED_ORIGINS`

Required for browser-facing deployments.

Example:

```text
CSRF_TRUSTED_ORIGINS=[
  "https://care.example.org",
  "https://api.care.example.org"
]
```

Origins SHALL include schemes.

## 6.5 `CORS_ALLOWED_ORIGINS`

Required when the frontend uses a separate origin.

Example:

```text
CORS_ALLOWED_ORIGINS=[
  "https://care.example.org"
]
```

Production SHALL not enable unrestricted CORS.

## 6.6 `CORS_ALLOWED_ORIGIN_REGEXES`

Optional.

Use only when exact origin lists are insufficient.

Regular expressions SHALL be reviewed to avoid broad origin access.

## 6.7 `DJANGO_SECURE_SSL_REDIRECT`

Recommended production value:

```text
true
```

Cloud Run proxy handling SHALL correctly recognize forwarded HTTPS.

## 6.8 `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS`

Recommended after the domain strategy is confirmed.

## 6.9 `DJANGO_SECURE_HSTS_PRELOAD`

SHALL not be enabled casually.

Preload has operational consequences outside CARE.

## 6.10 `DJANGO_SECURE_CONTENT_TYPE_NOSNIFF`

Recommended value:

```text
true
```

---

# 7. Cloud Run Configuration

## 7.1 `PORT`

Provided automatically by Cloud Run.

The API and HTTP worker SHALL listen on:

```text
0.0.0.0:${PORT}
```

The application SHALL not require a fixed production port.

## 7.2 `CARE_PROCESS_ROLE`

Recommended.

Supported values:

```text
api
task_worker
postgres_queue_worker
job
celery_worker
```

Example:

```text
CARE_PROCESS_ROLE=api
```

The role MAY control:

- startup command;
- route availability;
- health checks;
- enabled integrations;
- logging metadata.

It SHALL not alter clinical business behavior.

## 7.3 `GUNICORN_WORKERS`

Optional.

Conservative initial value:

```text
GUNICORN_WORKERS=1
```

The value SHALL be selected together with:

- Cloud Run concurrency;
- memory;
- database connections;
- thread count.

## 7.4 `GUNICORN_THREADS`

Optional.

Example:

```text
GUNICORN_THREADS=4
```

The total request concurrency per instance SHALL remain compatible with
database and file-streaming behavior.

## 7.5 `GUNICORN_TIMEOUT`

Optional.

The value SHALL support expected API and file-transfer durations.

It SHALL not be increased indefinitely to hide inefficient or inappropriate
request workloads.

## 7.6 `GUNICORN_GRACEFUL_TIMEOUT`

Optional.

Should allow orderly request completion during revision replacement.

## 7.7 `GUNICORN_KEEPALIVE`

Optional.

Use a conservative value compatible with Cloud Run proxy behavior.

## 7.8 Cloud Run minimum instances

Managed through Terraform rather than Django environment variables.

Recommended default:

```text
API: 0
HTTP task worker: 0
```

A minimum greater than zero requires explicit cost justification.

## 7.9 Cloud Run maximum instances

Managed through Terraform.

The value SHALL respect the database connection budget.

---

# 8. Google Cloud Identity

## 8.1 `GCP_PROJECT_ID`

Required for GCP environments.

Example:

```text
GCP_PROJECT_ID=care-production
```

## 8.2 `GCP_REGION`

Required.

Example:

```text
GCP_REGION=us-central1
```

The selected region SHOULD align with:

- Cloud Run;
- Cloud SQL;
- Cloud Tasks location;
- storage location where practical;
- expected users;
- legal and organizational requirements.

## 8.3 `GOOGLE_APPLICATION_CREDENTIALS`

SHALL normally be absent in Cloud Run.

Cloud Run SHALL use its attached service account and Application Default
Credentials.

This variable MAY be used locally for controlled integration tests.

Committed credential files are prohibited.

---

# 9. Database Configuration

## 9.1 `DATABASE_URL`

Required secret or protected configuration.

Example conceptual value:

```text
postgresql://care:<password>@/<database>?host=/cloudsql/<connection-name>
```

The exact form SHALL follow the chosen Cloud SQL connection mechanism and the
existing CARE environment parser.

The URL SHALL not be logged.

## 9.2 `CONN_MAX_AGE`

Required to be deliberately configured.

Conservative initial example:

```text
CONN_MAX_AGE=60
```

The final value SHALL be determined through testing.

A longer lifetime may reduce connection setup overhead but retain more
connections.

## 9.3 `CONN_HEALTH_CHECKS`

Recommended where supported.

Example:

```text
CONN_HEALTH_CHECKS=true
```

## 9.4 `CARE_DATABASE_APPLICATION_NAME`

Optional.

May identify application role in PostgreSQL sessions.

Examples:

```text
care-api
care-worker
care-jobs
```

## 9.5 `CARE_DATABASE_STATEMENT_TIMEOUT_MS`

Optional.

A deployment MAY configure a statement timeout.

It SHALL be tested against report generation, cleanup and administrative
commands.

## 9.6 `CARE_DATABASE_LOCK_TIMEOUT_MS`

Optional.

Useful to prevent indefinitely waiting on locks.

The value SHALL not cause normal migrations or transactions to fail
unnecessarily.

---

# 10. Database Initialization Configuration

## 10.1 `CARE_CREATE_CACHE_TABLE`

Optional deployment-pipeline variable.

Example:

```text
CARE_CREATE_CACHE_TABLE=true
```

It indicates whether the initialization pipeline should run:

```bash
python manage.py createcachetable
```

The application runtime SHALL not create tables automatically on every startup.

## 10.2 `CARE_RUN_SYNC_PERMISSIONS`

Optional job control.

Example:

```text
CARE_RUN_SYNC_PERMISSIONS=true
```

## 10.3 `CARE_RUN_SYNC_VALUESETS`

Optional job control.

Example:

```text
CARE_RUN_SYNC_VALUESETS=true
```

These variables belong to deployment or job orchestration rather than
request-time application behavior.

---

# 11. Storage Backend Selection

## 11.1 General rule

Storage provider selection SHALL occur through Django `STORAGES`.

Application code SHALL use logical aliases.

The application SHALL not use:

```text
CARE_STORAGE_PROVIDER=gcp
```

inside business logic to branch between SDKs.

The settings module MAY use provider selection to construct `STORAGES`.

## 11.2 `CARE_STORAGE_BACKEND`

**Implemented in IS-01** (`config/storage.py`, `config/settings/base.py`).

Supported values:

```text
s3
gcs
```

Intended use:

```text
s3   -> MinIO, AWS S3 or compatible service  (default)
gcs  -> GCP production
```

Default:

```text
CARE_STORAGE_BACKEND=s3
```

The default preserves the existing local MinIO behaviour, so no local
configuration change is required.

Production GCP value:

```text
CARE_STORAGE_BACKEND=gcs
```

An unsupported value raises `ImproperlyConfigured` at startup, naming the
supported values.

`filesystem` is **not** a supported value. Per ES-01 §9 a filesystem backend may
remain test-only and is not exposed as a production option; tests substitute
`django.core.files.storage.InMemoryStorage` through `override_settings` instead.

## 11.3 `CARE_PATIENT_STORAGE_ALIAS`

Optional.

Default:

```text
patient
```

Changing logical aliases is discouraged.

## 11.4 `CARE_FACILITY_STORAGE_ALIAS`

Optional.

Default:

```text
facility
```

## 11.5 `CARE_REPORT_STORAGE_ALIAS`

Optional.

Default:

```text
report
```

---

# 12. GCS Storage Configuration

## 12.1 `CARE_PATIENT_STORAGE_BUCKET`

Required when GCS is selected.

## 12.2 `CARE_FACILITY_STORAGE_BUCKET`

Required when GCS is selected.

## 12.3 `CARE_REPORT_STORAGE_BUCKET`

Required when GCS is selected.

The report bucket MAY equal the patient bucket.

Logical aliases SHALL remain separate.

## 12.4 `GCS_PROJECT_ID`

Optional alias.

The implementation SHOULD normally reuse:

```text
GCP_PROJECT_ID
```

A separate project value MAY be supported for cross-project buckets only if
required.

## 12.5 `GCS_LOCATION`

Infrastructure-level value.

Managed by Terraform when creating buckets.

It is not normally needed by Django after bucket creation.

## 12.6 `GCS_DEFAULT_ACL`

Production SHOULD not depend on public or object-level default ACLs.

Uniform bucket-level access is preferred.

## 12.7 `GCS_QUERYSTRING_AUTH`

Recommended target value:

```text
false
```

because the normal file flow passes through Django and does not expose signed
provider URLs.

## 12.8 `GCS_FILE_OVERWRITE`

The value SHALL reflect CARE's object-name policy.

**Resolved in IS-01: overwrite SHALL be enabled, on every object-storage alias
and on both backends.** `config/storage.py` sets `file_overwrite: True`
unconditionally; it is not driven by an environment variable.

The earlier suggestion that `false` "may be appropriate" for unique, immutable
names is **incorrect**, and tested to be so. `file_overwrite = False` does not
reject a duplicate name — Django's `Storage.get_available_name` silently *renames*
the object, returning e.g. `patient/<internal_name>_a1b2c3`. CARE derives the key
from `internal_name` on every subsequent read, so the rename is never recorded
and the database row would point at an object that does not exist. That is
precisely the "duplicate-name handling affects database object references"
hazard this section warns about, and `false` causes it rather than preventing it.

`True` also matches the behaviour being replaced: `boto3.put_object` overwrote
unconditionally.

In practice collisions do not occur — `internal_name` is a UUID plus a timestamp
— so the setting matters only as a guarantee.

Verified by:

- `care/utils/tests/test_storage_config.py` — every alias is built with
  `file_overwrite: True`;
- `care/emr/tests/test_storage.py` — against real MinIO, re-saving returns the
  same name and replaces the content;
- the same file demonstrates the failure mode: `InMemoryStorage`, which has no
  such option, renames on collision.

## 12.9 `GCS_MAX_MEMORY_SIZE`

Optional backend setting.

This value SHALL be coordinated with Django upload handlers and Cloud Run
memory.

It SHALL not cause large objects to be loaded fully into memory.

---

# 13. S3 and MinIO Configuration

These settings apply when:

```text
CARE_STORAGE_BACKEND=s3
```

**Corrected 2026-08-07 to match the implementation.** Earlier revisions of this
section specified `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_ENDPOINT_URL`,
`S3_REGION_NAME`, `S3_ADDRESSING_STYLE` and `S3_SIGNATURE_VERSION`. **No such
settings exist.** ES-01 §11.1 required reusing the tracked local configuration
rather than inventing a parallel set, so the credential and endpoint variables
below are the pre-existing ones.

## 13.1 Credentials and endpoints, per alias

Each alias draws from its own set. All have defaults, so a local checkout needs
no new value.

| Alias | Region | Key | Secret | Endpoint |
| --- | --- | --- | --- | --- |
| `patient` | `FILE_UPLOAD_REGION` | `FILE_UPLOAD_KEY` | `FILE_UPLOAD_SECRET` | `FILE_UPLOAD_BUCKET_ENDPOINT` |
| `report` | `FILE_UPLOAD_REGION` | `FILE_UPLOAD_KEY` | `FILE_UPLOAD_SECRET` | `FILE_UPLOAD_BUCKET_ENDPOINT` |
| `facility` | `FACILITY_S3_REGION_CODE` | `FACILITY_S3_KEY` | `FACILITY_S3_SECRET` | `FACILITY_S3_BUCKET_ENDPOINT` |

Each falls back to the shared `BUCKET_REGION` / `BUCKET_KEY` / `BUCKET_SECRET` /
`BUCKET_ENDPOINT`. An endpoint is emitted only when set, so AWS S3 works without
one; MinIO sets `BUCKET_ENDPOINT=http://minio:9000`.

## 13.2 `BUCKET_PROVIDER`

Credential source, not provider selection — provider selection is
`CARE_STORAGE_BACKEND` alone.

```text
AWS_ROLE_BASED  -> omit key, secret and endpoint; the SDK resolves the
                   instance role
anything else   -> supply key and secret explicitly
```

## 13.3 Bucket variables

```text
CARE_PATIENT_STORAGE_BUCKET
CARE_FACILITY_STORAGE_BUCKET
CARE_REPORT_STORAGE_BUCKET
```

Defaulting to `FILE_UPLOAD_BUCKET`, `FACILITY_S3_BUCKET` and
`FILE_UPLOAD_BUCKET` respectively. These are the **only** place a bucket name is
resolved; nothing else derives one.

## 13.4 Not configurable

`addressing_style` and `signature_version` are **not** exposed. botocore's
defaults are used, which are correct for both AWS S3 and MinIO (verified against
the local MinIO container).

**Known limitation:** an S3-compatible provider that requires explicit path-style
addressing or `s3v4` signing cannot currently be configured. No such provider is
in use. Adding them is a small change to `build_object_storage` in
`config/storage.py` if one appears.

---

# 14. Static File Configuration

## 14.1 `STATIC_URL`

Existing CARE value MAY remain.

## 14.2 `STATIC_ROOT`

Set in Django settings or image build configuration.

## 14.3 Static backend

The target backend remains:

```text
whitenoise.storage.CompressedManifestStaticFilesStorage
```

No runtime variable is required unless the project intentionally makes it
configurable.

## 14.4 `CARE_COLLECTSTATIC`

Build-time or deployment variable only.

The production image SHOULD run `collectstatic` during build.

The API SHALL not run it during every instance startup.

---

# 15. Upload Configuration

## 15.1 `CARE_MAX_UPLOAD_SIZE`

Required to be explicitly defined.

Example:

```text
CARE_MAX_UPLOAD_SIZE=26214400
```

This example represents 25 MiB.

The actual limit SHALL be selected after testing.

## 15.2 `FILE_UPLOAD_MAX_MEMORY_SIZE`

Recommended.

Defines when Django moves uploaded content from memory to temporary files.

Example:

```text
FILE_UPLOAD_MAX_MEMORY_SIZE=2621440
```

The exact parser may require this value through Django settings rather than a
direct environment variable name.

## 15.3 `DATA_UPLOAD_MAX_MEMORY_SIZE`

Recommended.

Controls total request-data memory behavior.

It SHALL be large enough for supported requests and smaller than dangerous
resource-exhaustion levels.

## 15.4 `FILE_UPLOAD_TEMP_DIR`

Optional.

Cloud Run's writable filesystem is ephemeral.

A temporary directory MAY use:

```text
/tmp
```

Temporary files SHALL not be treated as durable.

## 15.5 `CARE_ALLOWED_UPLOAD_MIME_TYPES`

Optional override.

The implementation SHOULD continue using CARE's existing allowlists unless
deployment-specific changes are required.

## 15.6 `CARE_ALLOWED_UPLOAD_EXTENSIONS`

Optional override.

## 15.7 `CARE_BLOCKED_UPLOAD_EXTENSIONS`

Optional override.

Security-sensitive defaults SHALL remain active.

---

# 16. Download Configuration

## 16.1 `CARE_INLINE_MIME_TYPES`

Optional.

Defines MIME types returned with:

```text
Content-Disposition: inline
```

Likely candidates:

```text
application/pdf
selected image types
```

## 16.2 `CARE_DOWNLOAD_CHUNK_SIZE`

Optional.

May control streaming chunk size where the implementation exposes it.

The value SHALL be benchmarked.

## 16.3 `CARE_ENABLE_RANGE_REQUESTS`

Optional.

Default:

```text
false
```

unless media-range support is implemented and tested.

---

# 17. Task Backend Selection

## 17.1 `CARE_TASK_BACKEND`

Required.

Supported values:

```text
cloud_tasks
celery
postgres
```

The `postgres` value SHALL be accepted only if the PostgreSQL queue backend is
implemented and approved.

Recommended GCP value:

```text
CARE_TASK_BACKEND=cloud_tasks
```

Local upstream-compatible value:

```text
CARE_TASK_BACKEND=celery
```

## 17.2 `CARE_TASK_DEFAULT_DELAY_SECONDS`

Optional.

Default:

```text
0
```

## 17.3 `CARE_TASK_PAYLOAD_VERSION`

Optional.

Recommended when task payload schemas become versioned.

Example:

```text
CARE_TASK_PAYLOAD_VERSION=1
```

## 17.4 `CARE_TASK_MAX_PAYLOAD_BYTES`

Recommended.

Prevents oversized task payloads.

Tasks SHOULD normally contain identifiers rather than clinical records.

---

# 18. Cloud Tasks Configuration

Required when:

```text
CARE_TASK_BACKEND=cloud_tasks
```

## 18.1 `GCP_TASKS_PROJECT_ID`

Optional.

Defaults to:

```text
GCP_PROJECT_ID
```

## 18.2 `GCP_TASKS_LOCATION`

Required.

Example:

```text
GCP_TASKS_LOCATION=us-central1
```

## 18.3 `GCP_TASKS_QUEUE`

Required.

Example:

```text
GCP_TASKS_QUEUE=care-default
```

Multiple queues MAY later use task-class-specific variables.

## 18.4 `GCP_WORKER_URL`

Required.

Example:

```text
GCP_WORKER_URL=https://care-prod-worker-...run.app/internal/tasks/execute/
```

The URL SHALL target the private worker service.

## 18.5 `GCP_TASKS_SERVICE_ACCOUNT`

Required.

This is the service account identity attached to OIDC task requests.

Example:

```text
care-tasks-invoker@care-production.iam.gserviceaccount.com
```

## 18.6 `GCP_TASKS_OIDC_AUDIENCE`

Recommended.

Often equal to the worker service origin.

It SHALL match worker IAM expectations.

## 18.7 `GCP_TASKS_DEFAULT_DEADLINE_SECONDS`

Optional.

The value SHALL remain within Cloud Tasks and Cloud Run supported limits.

Different queues MAY use different infrastructure-level deadlines.

## 18.8 `GCP_TASKS_DEFAULT_QUEUE`

Optional alias for `GCP_TASKS_QUEUE`.

The project SHOULD avoid maintaining redundant names indefinitely.

## 18.9 Retry configuration

Retry policy SHOULD be managed in Terraform.

Examples:

```text
max attempts
max retry duration
minimum backoff
maximum backoff
maximum doublings
```

Task code SHALL not silently override infrastructure policy without
documentation.

---

# 19. Cloud Tasks Worker Configuration

## 19.1 `CARE_TASK_HANDLER_ENDPOINT_ENABLED`

Optional.

Recommended values:

```text
API role: false
task_worker role: true
```

This variable MAY prevent internal task routes from being exposed by the public
API service.

## 19.2 `CARE_TASK_ALLOWED_QUEUE_NAMES`

Optional defense-in-depth configuration.

The worker MAY validate expected Cloud Tasks queue headers.

This SHALL not replace IAM.

## 19.3 `CARE_TASK_LOG_PAYLOAD`

Production-required value:

```text
false
```

Full task payload logging is prohibited.

## 19.4 `CARE_TASK_HANDLER_TIMEOUT_SECONDS`

Optional application-level timeout.

It SHALL remain lower than the infrastructure request deadline when enforced.

## 19.5 `CARE_TASK_RETRYABLE_EXCEPTIONS`

SHOULD be defined in code, not as arbitrary import paths from environment
variables.

Configuration MAY control categories, but SHALL not enable arbitrary code
loading.

---

# 20. Celery Configuration

Used when:

```text
CARE_TASK_BACKEND=celery
```

## 20.1 `CELERY_BROKER_URL`

Required.

Common local value:

```text
redis://redis:6379/0
```

## 20.2 `CELERY_RESULT_BACKEND`

Optional depending on CARE call-site requirements.

Existing local compatibility MAY use the broker URL.

## 20.3 `CELERY_TASK_ALWAYS_EAGER`

Test-only option.

SHALL not be enabled in production unintentionally.

## 20.4 `CELERY_BEAT_ENABLED`

Recommended explicit variable.

Local traditional value:

```text
true
```

GCP value:

```text
false
```

The GCP profile SHALL not run Celery Beat.

## 20.5 `CELERY_WORKER_CONCURRENCY`

Optional.

Must respect database and Redis connection budgets.

---

# 21. PostgreSQL Task Queue Configuration

This section applies only if the optional queue backend is approved.

## 21.1 `CARE_POSTGRES_QUEUE_SCHEMA`

Optional.

Example:

```text
CARE_POSTGRES_QUEUE_SCHEMA=care_tasks
```

## 21.2 `CARE_POSTGRES_QUEUE_NAMES`

Optional list.

Example:

```text
CARE_POSTGRES_QUEUE_NAMES=["default","reports","email"]
```

Do not create multiple queues without a workload reason.

## 21.3 `CARE_POSTGRES_WORKER_CONCURRENCY`

Optional.

Conservative default:

```text
1
```

## 21.4 `CARE_POSTGRES_WORKER_POLL_INTERVAL`

Optional.

Only relevant if the chosen queue implementation polls.

## 21.5 `CARE_POSTGRES_WORKER_HEARTBEAT_SECONDS`

Optional.

Used for worker-health diagnostics.

## 21.6 `CARE_POSTGRES_JOB_RETENTION_DAYS`

Optional.

Defines retention for completed or failed task records.

## 21.7 `CARE_POSTGRES_QUEUE_ENABLED`

May be redundant with `CARE_TASK_BACKEND=postgres`.

The implementation SHOULD prefer one authoritative switch.

---

# 22. Cache Backend Selection

## 22.1 `CARE_CACHE_BACKEND`

Required.

Supported values:

```text
postgres
locmem
redis
dummy
```

Recommended low-cost GCP value:

```text
CARE_CACHE_BACKEND=postgres
```

Local compatibility value:

```text
CARE_CACHE_BACKEND=redis
```

Test value:

```text
CARE_CACHE_BACKEND=dummy
```

or:

```text
CARE_CACHE_BACKEND=locmem
```

depending on test behavior.

---

# 23. PostgreSQL Cache Configuration

Required when:

```text
CARE_CACHE_BACKEND=postgres
```

## 23.1 `CARE_CACHE_TABLE`

Recommended.

Default:

```text
care_cache
```

## 23.2 `CARE_CACHE_TIMEOUT`

Optional.

Defines the default Django cache timeout.

Example:

```text
CARE_CACHE_TIMEOUT=300
```

## 23.3 `CARE_CACHE_MAX_ENTRIES`

Optional.

Example:

```text
CARE_CACHE_MAX_ENTRIES=10000
```

The final value SHALL be based on measured usage.

## 23.4 `CARE_CACHE_CULL_FREQUENCY`

Optional.

Example:

```text
CARE_CACHE_CULL_FREQUENCY=3
```

## 23.5 `CARE_CACHE_KEY_PREFIX`

Recommended.

Example:

```text
care:prod
```

This helps separate environments or logical uses.

## 23.6 `CARE_CACHE_VERSION`

Optional Django cache version value.

## 23.7 Table creation

The application SHALL fail clearly or report unhealthy configuration when the
selected database cache table does not exist.

It SHALL not create the table during ordinary request startup.

---

# 24. LocMem Cache Configuration

## 24.1 `CARE_CACHE_LOCATION`

Optional.

Example:

```text
care-local-cache
```

## 24.2 `CARE_CACHE_MAX_ENTRIES`

Optional.

LocMem remains process-local and ephemeral.

The configuration SHALL not imply cross-instance consistency.

---

# 25. Redis Cache Configuration

Required when:

```text
CARE_CACHE_BACKEND=redis
```

## 25.1 `REDIS_CACHE_URL`

Required secret.

Example:

```text
rediss://default:<password>@<host>:6379/0
```

## 25.2 `REDIS_CACHE_PREFIX`

Recommended.

Example:

```text
care:prod:cache
```

## 25.3 `REDIS_CACHE_TIMEOUT`

Optional.

## 25.4 `REDIS_CACHE_SOCKET_TIMEOUT`

Recommended.

## 25.5 `REDIS_CACHE_CONNECT_TIMEOUT`

Recommended.

## 25.6 `REDIS_CACHE_IGNORE_EXCEPTIONS`

Default SHOULD depend on cache purpose.

For performance-only cache:

```text
true
```

may be acceptable.

For correctness-sensitive state:

```text
false
```

or a dedicated non-cache backend is preferred.

---

# 26. Rate-Limit Backend Selection

## 26.1 `CARE_RATE_LIMIT_BACKEND`

Required.

Supported values:

```text
postgres
redis
```

Recommended Redis-free GCP value:

```text
CARE_RATE_LIMIT_BACKEND=postgres
```

LocMem SHALL not be a supported globally consistent production backend.

## 26.2 `CARE_RATE_LIMIT_DEFAULT`

Existing CARE-compatible default MAY be:

```text
5/10m
```

The exact syntax SHALL remain compatible with the selected library.

## 26.3 `DISABLE_RATELIMIT`

Production-required value:

```text
false
```

Disabling rate limiting in production SHALL require an explicit exceptional
decision.

## 26.4 `CARE_RATE_LIMIT_FAILURE_POLICY`

Recommended.

Supported conceptual values:

```text
fail_closed
fail_open
controlled_error
```

Security-sensitive endpoints SHOULD not silently fail open.

---

# 27. PostgreSQL Rate-Limit Configuration

## 27.1 `CARE_RATE_LIMIT_TABLE`

Optional.

Required only if explicit database models or tables are introduced.

## 27.2 `CARE_RATE_LIMIT_RETENTION_SECONDS`

Optional.

Defines cleanup retention for expired counters.

## 27.3 `CARE_RATE_LIMIT_CLEANUP_BATCH_SIZE`

Optional.

Used by maintenance jobs where applicable.

---

# 28. Redis Rate-Limit Configuration

Required when:

```text
CARE_RATE_LIMIT_BACKEND=redis
```

## 28.1 `REDIS_RATE_LIMIT_URL`

Required secret.

It MAY equal `REDIS_CACHE_URL`, but SHALL be configurable independently.

## 28.2 `REDIS_RATE_LIMIT_PREFIX`

Recommended.

Example:

```text
care:prod:ratelimit
```

## 28.3 `REDIS_RATE_LIMIT_SOCKET_TIMEOUT`

Recommended.

## 28.4 Failure behavior

The configured outage policy SHALL be tested.

---

# 29. Transient-State Backend Selection

## 29.1 `CARE_TRANSIENT_STATE_BACKEND`

Required.

Supported values:

```text
postgres
redis
```

Recommended low-cost GCP value:

```text
CARE_TRANSIENT_STATE_BACKEND=postgres
```

## 29.2 Durable versus disposable state

The variable SHALL select shared short-lived state only.

Correctness-critical or auditable state SHOULD use explicit PostgreSQL models
regardless of cache backend.

---

# 30. PostgreSQL Transient-State Configuration

## 30.1 `CARE_TRANSIENT_STATE_TABLE`

Optional.

Used only if a dedicated generic state table is implemented.

A generic table SHOULD not replace domain-specific models without need.

## 30.2 `CARE_TRANSIENT_STATE_DEFAULT_TTL`

Optional.

## 30.3 `CARE_TRANSIENT_STATE_CLEANUP_BATCH_SIZE`

Optional.

---

# 31. Redis Transient-State Configuration

## 31.1 `REDIS_TRANSIENT_STATE_URL`

Required when Redis transient state is selected.

## 31.2 `REDIS_TRANSIENT_STATE_PREFIX`

Recommended.

Example:

```text
care:prod:state
```

## 31.3 `REDIS_TRANSIENT_STATE_DEFAULT_TTL`

Optional.

---

# 32. Report Progress Configuration

## 32.1 `CARE_REPORT_PROGRESS_BACKEND`

Recommended explicit variable.

Supported values:

```text
database_model
cache
```

When:

```text
cache
```

is selected, the configured shared cache backend is used.

When:

```text
database_model
```

is selected, durable task or report-progress records are used.

## 32.2 Recommended initial value

If users need reliable cross-instance visibility and failure history:

```text
CARE_REPORT_PROGRESS_BACKEND=database_model
```

If disposable progress is sufficient:

```text
CARE_REPORT_PROGRESS_BACKEND=cache
```

## 32.3 `CARE_REPORT_PROGRESS_TIMEOUT`

Required only for cache-backed progress.

Example:

```text
CARE_REPORT_PROGRESS_TIMEOUT=600
```

The current two-minute behavior MAY be too short for real report generation and
SHALL be reviewed.

---

# 33. Optional Redis Provider Configuration

## 33.1 Provider-neutral configuration

The application SHOULD not require a provider name.

Standard Redis URLs should be sufficient.

## 33.2 `REDIS_SSL_CERT_REQS`

Optional.

Production SHOULD verify certificates.

Disabling verification SHALL require explicit justification.

## 33.3 `REDIS_MAX_CONNECTIONS`

Recommended.

The value SHALL respect provider plan limits and Cloud Run scaling.

## 33.4 `REDIS_HEALTH_CHECK_INTERVAL`

Optional.

## 33.5 `REDIS_RETRY_ON_TIMEOUT`

Optional.

Behavior SHALL be selected per responsibility.

## 33.6 Upstash

An Upstash deployment MAY configure:

```text
REDIS_CACHE_URL=rediss://...
REDIS_RATE_LIMIT_URL=rediss://...
REDIS_TRANSIENT_STATE_URL=rediss://...
```

No `USE_UPSTASH` variable is required.

---

# 34. Email Configuration

## 34.1 `EMAIL_BACKEND`

Default production value MAY remain:

```text
django.core.mail.backends.smtp.EmailBackend
```

## 34.2 `EMAIL_HOST`

Required when SMTP is enabled.

## 34.3 `EMAIL_PORT`

Required.

## 34.4 `EMAIL_HOST_USER`

Secret or protected value.

## 34.5 `EMAIL_HOST_PASSWORD`

Required secret when provider authentication requires it.

## 34.6 `EMAIL_USE_TLS`

Recommended according to provider requirements.

## 34.7 `EMAIL_USE_SSL`

Mutually constrained with TLS according to Django behavior.

## 34.8 `DEFAULT_FROM_EMAIL`

Required.

Example:

```text
CARE <no-reply@example.org>
```

## 34.9 `SERVER_EMAIL`

Recommended for framework-generated error notifications where used.

## 34.10 `CARE_EMAIL_TASK_QUEUE`

Optional.

May select a dedicated queue name when task isolation is implemented.

---

# 35. Sentry Configuration

## 35.1 `SENTRY_DSN`

Optional secret.

If absent, Sentry SHALL remain disabled.

## 35.2 `SENTRY_ENVIRONMENT`

Recommended.

Defaults to:

```text
CARE_ENVIRONMENT
```

## 35.3 `SENTRY_TRACES_SAMPLE_RATE`

Optional.

Production value SHALL be chosen with privacy and cost considerations.

## 35.4 `SENTRY_PROFILES_SAMPLE_RATE`

Optional.

## 35.5 `SENTRY_EVENT_LEVEL`

Optional.

## 35.6 Integration selection

The GCP settings SHALL enable integrations according to active backends:

```text
Django integration -> normally enabled
Celery integration -> only when Celery is used
Redis integration -> only when Redis is used
```

---

# 36. Logging Configuration

## 36.1 `CARE_LOG_FORMAT`

Supported values SHOULD include:

```text
json
text
```

Recommended GCP value:

```text
json
```

## 36.2 `CARE_LOG_LEVEL`

Recommended default:

```text
INFO
```

Production `DEBUG` logging SHALL not be enabled broadly without review.

## 36.3 `CARE_LOG_REQUEST_BODIES`

Production-required value:

```text
false
```

## 36.4 `CARE_LOG_TASK_PAYLOADS`

Production-required value:

```text
false
```

## 36.5 `CARE_LOG_FILE_CONTENTS`

Production-required value:

```text
false
```

## 36.6 `CARE_LOG_SQL`

Production default:

```text
false
```

Temporary SQL logging MAY be enabled in controlled non-production
environments.

## 36.7 `CARE_REQUEST_ID_HEADER`

Optional.

Example:

```text
X-Request-ID
```

---

# 37. Health-Check Configuration

## 37.1 `CARE_HEALTH_DATABASE_ENABLED`

Recommended:

```text
true
```

## 37.2 `CARE_HEALTH_CACHE_ENABLED`

Recommended when the selected cache is required for normal operation.

## 37.3 `CARE_HEALTH_REDIS_ENABLED`

SHALL default according to active Redis responsibilities.

It SHALL not be required in a Redis-free profile.

## 37.4 `CARE_HEALTH_CELERY_ENABLED`

GCP Cloud Tasks profile:

```text
false
```

Local Celery profile:

```text
true
```

## 37.5 `CARE_HEALTH_POSTGRES_QUEUE_ENABLED`

Only when the PostgreSQL queue backend is selected.

## 37.6 `CARE_HEALTH_STORAGE_ENABLED`

Optional.

A storage diagnostic check MAY be useful.

It SHALL avoid writing test objects on every public health request.

## 37.7 `CARE_HEALTH_PUBLIC_DETAILS`

Production-required value:

```text
false
```

Detailed dependency diagnostics SHOULD require operator authorization.

---

# 38. Cloud Run Job Configuration

## 38.1 `CARE_JOB_NAME`

Recommended log metadata.

Examples:

```text
migrate
sync-permissions
cleanup-incomplete-uploads
```

## 38.2 `CARE_JOB_COMMAND`

Prefer command configuration through the Cloud Run Job container command
rather than arbitrary runtime shell execution.

## 38.3 `CARE_JOB_TIMEOUT_SECONDS`

Infrastructure-level setting managed by Terraform.

## 38.4 `CARE_JOB_MAX_RETRIES`

Infrastructure-level setting.

## 38.5 `CARE_JOB_DRY_RUN`

Optional for commands supporting non-destructive previews.

Destructive jobs SHOULD support a dry-run mode where practical.

---

# 39. Cloud Scheduler Configuration

Scheduler configuration SHOULD primarily live in Terraform.

Per schedule, define:

```text
name
cron expression
timezone
target
authentication
retry policy
enabled state
```

## 39.1 `CARE_SCHEDULER_TIMEZONE`

Optional shared default.

The timezone SHALL be explicit.

It SHALL not inherit an unrelated Celery timezone accidentally.

## 39.2 Cleanup cadence

Variables MAY control schedule creation, but Terraform remains authoritative.

Examples:

```text
CARE_EXPIRED_TOKEN_CLEANUP_CRON
CARE_INCOMPLETE_UPLOAD_CLEANUP_CRON
```

The application SHALL not dynamically register GCP production schedules at
startup.

---

# 40. Authentication and JWT Configuration

CARE's existing authentication configuration SHALL remain authoritative.

Relevant secrets and variables may include:

```text
JWKS_BASE64
JWT-related keys
token lifetimes
issuer and audience settings
```

These SHALL be preserved during GCP adaptation.

Private signing material SHALL be stored in Secret Manager.

Authentication behavior SHALL not change merely because the application moves
to Cloud Run.

---

# 41. External Service Configuration

Existing CARE integrations MAY require variables for:

```text
Snowstorm or terminology services
SMS providers
SMTP
Sentry
other plugins
```

Each integration SHALL define:

- required variables;
- whether values are secret;
- timeout;
- failure behavior;
- health-check behavior;
- enabled state.

Optional integrations SHALL not prevent API startup when disabled.

---

# 42. Plugin Configuration

Plugins may add environment variables and dependencies.

Required production plugins SHALL be inventoried.

A plugin SHALL not be enabled without confirming compatibility with:

- GCP settings;
- Django Storage API;
- Cloud Tasks or selected task backend;
- Redis-free operation;
- Cloud Run startup;
- empty-database initialization.

Plugin configuration SHALL not be mixed into the core GCP contract without a
documented reason.

---

# 43. Role-Specific Variable Matrix

| Variable group | API | HTTP worker | Jobs | PostgreSQL queue worker | Celery worker |
|---|---:|---:|---:|---:|---:|
| Django core | Required | Required | Required | Required | Required |
| Database | Required | Required | Required | Required | Required |
| Storage | Required | As handlers require | As commands require | As tasks require | As tasks require |
| Cloud Tasks enqueue | Usually required | Optional | Optional | No | No |
| Cloud Tasks worker URL | Required for enqueue | No | Optional | No | No |
| Task handler endpoint | No | Required | No | No | No |
| PostgreSQL queue config | No unless producer | No | Optional | Required | No |
| Celery broker | No | No | No | No | Required |
| Redis cache | Only if selected | Only if selected | Only if selected | Only if selected | Often |
| Email | As required | As required | Rarely | As tasks require | As tasks require |

Variables SHALL be injected only where needed where practical.

---

# 44. Default GCP Profile

Recommended initial configuration:

```text
DJANGO_SETTINGS_MODULE=config.settings.deployment
CARE_ENVIRONMENT=prod
DJANGO_DEBUG=false

CARE_PROCESS_ROLE=api

CARE_STORAGE_BACKEND=gcs
CARE_TASK_BACKEND=cloud_tasks
CARE_CACHE_BACKEND=postgres
CARE_RATE_LIMIT_BACKEND=postgres
CARE_TRANSIENT_STATE_BACKEND=postgres
CARE_REPORT_PROGRESS_BACKEND=database_model

GCP_PROJECT_ID=<project>
GCP_REGION=<region>

CARE_PATIENT_STORAGE_BUCKET=<bucket>
CARE_FACILITY_STORAGE_BUCKET=<bucket>
CARE_REPORT_STORAGE_BUCKET=<bucket>

GCP_TASKS_LOCATION=<location>
GCP_TASKS_QUEUE=<queue>
GCP_WORKER_URL=<private-worker-url>
GCP_TASKS_SERVICE_ACCOUNT=<invoker-service-account>

CARE_LOG_FORMAT=json
CARE_LOG_LEVEL=INFO
CARE_LOG_REQUEST_BODIES=false
CARE_LOG_TASK_PAYLOADS=false
```

Secrets are injected separately.

This profile SHALL start without any Redis variable.

---

# 45. Local Upstream-Compatible Profile

Conceptual local configuration:

```text
DJANGO_SETTINGS_MODULE=config.settings.local
CARE_ENVIRONMENT=dev

CARE_STORAGE_BACKEND=s3
CARE_TASK_BACKEND=celery
CARE_CACHE_BACKEND=redis
CARE_RATE_LIMIT_BACKEND=redis
CARE_TRANSIENT_STATE_BACKEND=redis

BUCKET_ENDPOINT=http://minio:9000
BUCKET_KEY=minioadmin
BUCKET_SECRET=minioadmin
FILE_UPLOAD_BUCKET=patient-bucket
FACILITY_S3_BUCKET=facility-bucket

CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

REDIS_CACHE_URL=redis://redis:6379/1
REDIS_RATE_LIMIT_URL=redis://redis:6379/2
REDIS_TRANSIENT_STATE_URL=redis://redis:6379/3
```

The storage variables are the pre-existing ones documented in §13; `S3_*` names
are not accepted. The shared `BUCKET_*` values serve every alias unless an
alias-specific `FILE_UPLOAD_*` or `FACILITY_S3_*` value overrides them.

The implementation MAY preserve existing local `REDIS_URL` compatibility while
introducing more specific variables gradually.

Development defaults SHALL not flow into production settings.

---

# 46. Optional Upstash Profile

Conceptual example:

```text
CARE_TASK_BACKEND=cloud_tasks
CARE_CACHE_BACKEND=redis
CARE_RATE_LIMIT_BACKEND=redis
CARE_TRANSIENT_STATE_BACKEND=redis

REDIS_CACHE_URL=rediss://...
REDIS_RATE_LIMIT_URL=rediss://...
REDIS_TRANSIENT_STATE_URL=rediss://...
```

The same URL MAY be reused initially.

The application SHALL not assume separate physical databases are supported or
necessary without checking the provider.

Namespaces or key prefixes SHALL isolate responsibilities.

---

# 47. Consolidated PostgreSQL Profile

Only if the PostgreSQL queue backend is approved:

```text
CARE_TASK_BACKEND=postgres
CARE_CACHE_BACKEND=postgres
CARE_RATE_LIMIT_BACKEND=postgres
CARE_TRANSIENT_STATE_BACKEND=postgres
```

This profile requires:

- queue schema;
- queue worker;
- worker health monitoring;
- task-record retention;
- additional Cloud SQL capacity planning.

It SHALL not be labeled scale-to-zero when immediate task execution requires an
active worker.

---

# 48. Test Profile

Conceptual fast test configuration:

```text
CARE_TASK_BACKEND=fake
CARE_CACHE_BACKEND=dummy
CARE_RATE_LIMIT_BACKEND=postgres
CARE_TRANSIENT_STATE_BACKEND=postgres
```

`CARE_STORAGE_BACKEND` is deliberately absent. Its only accepted values are `s3`
and `gcs` (§11.2); `filesystem` is not one of them and would raise
`ImproperlyConfigured` at startup. Tests that must avoid a real bucket
substitute `django.core.files.storage.InMemoryStorage` through
`override_settings` on `STORAGES`, which is a test-local override rather than a
configuration value.

A `fake` task backend MAY exist only in test settings.

Production settings SHALL reject it.

Provider integration tests SHALL explicitly override the fake backends.

---

# 49. Deprecated Compatibility Variables

During implementation, CARE may temporarily continue accepting existing
variables such as:

```text
REDIS_URL
BUCKET_PROVIDER
BUCKET_REGION
BUCKET_KEY
BUCKET_SECRET
BUCKET_ENDPOINT
BUCKET_EXTERNAL_ENDPOINT
FILE_UPLOAD_BUCKET
FILE_UPLOAD_BUCKET_ENDPOINT
FILE_UPLOAD_BUCKET_EXTERNAL_ENDPOINT
FACILITY_S3_BUCKET
FACILITY_S3_BUCKET_ENDPOINT
FACILITY_S3_BUCKET_EXTERNAL_ENDPOINT
```

Compatibility behavior SHALL:

- emit deprecation warnings where safe;
- map old values to new settings only when unambiguous;
- avoid mixing old and new values silently;
- define precedence clearly;
- document eventual removal.

Because the production deployment is greenfield, new GCP environments SHOULD
use only the new variables.

---

# 50. Configuration Precedence

Recommended precedence:

1. explicit new configuration variable;
2. supported compatibility variable;
3. safe non-secret default;
4. configuration error.

If both new and old variables are set with conflicting values:

- the new value MAY take precedence;
- startup SHOULD emit a warning;
- production MAY reject the conflict to avoid ambiguity.

Secret values SHALL never be printed in warnings.

---

# 51. Safe Defaults

Safe defaults MAY exist for:

```text
log level
cache timeout
task delay
process role in local development
non-secret feature toggles
```

Defaults SHALL not exist for production:

```text
Django secret key
database password
SMTP password
Redis password
private signing keys
service-account credentials
production bucket names
production trusted origins
```

---

# 52. Prohibited Production Defaults

The GCP settings SHALL reject or warn critically about:

```text
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=*
DISABLE_RATELIMIT=true
public storage configuration
default MinIO credentials
localhost database URL
localhost Redis URL
local MinIO endpoint
service-account JSON bundled in image
CARE_LOG_REQUEST_BODIES=true
CARE_LOG_TASK_PAYLOADS=true
```

The exact enforcement MAY differ between `dev`, `staging` and `prod`.

---

# 53. Startup Validation

At startup, CARE SHOULD validate:

- selected backend names;
- required variables for each backend;
- mutually incompatible settings;
- role-specific requirements;
- production security values;
- storage aliases;
- cache table configuration;
- worker URL format;
- queue location and name;
- Redis URL scheme when Redis is selected.

Startup validation SHALL avoid making destructive calls.

External connectivity checks belong in readiness or diagnostics, not settings
parsing.

---

# 54. Configuration Diagnostics

An authorized management command SHOULD display effective non-secret
configuration.

Conceptual command:

```bash
python manage.py check_gcp_configuration
```

It MAY report:

```text
environment
process role
storage backend and aliases
task backend
cache backend
rate-limit backend
transient-state backend
report-progress backend
required service availability
health-check selection
```

It SHALL redact:

```text
passwords
secret keys
tokens
complete URLs containing credentials
private key material
```

---

# 55. Configuration Test Matrix

At minimum, automated tests SHALL validate:

| Profile | Tasks | Cache | Rate limits | State | Storage |
|---|---|---|---|---|---|
| GCP default | Cloud Tasks | PostgreSQL | PostgreSQL | PostgreSQL | GCS |
| GCP Redis | Cloud Tasks | Redis | Redis | Redis | GCS |
| Local | Celery | Redis | Redis | Redis | MinIO/S3 |
| GCP LocMem | Cloud Tasks | LocMem | PostgreSQL | PostgreSQL | GCS |
| Consolidated PostgreSQL | PostgreSQL queue | PostgreSQL | PostgreSQL | PostgreSQL | configured storage |
| Test | fake/eager | Dummy | test backend | test backend | filesystem |

The consolidated profile applies only if implemented.

---

# 56. Configuration Change Procedure

Before changing production configuration:

1. identify affected services;
2. determine whether a new revision is required;
3. determine whether the value is secret;
4. test in staging;
5. review IAM and dependency implications;
6. deploy the new configuration;
7. run smoke tests;
8. monitor logs and metrics;
9. record the change.

Changing a backend value may require additional resources.

Example:

```text
CARE_CACHE_BACKEND=postgres -> redis
```

requires a valid Redis service and secret.

---

# 57. Backend Change Semantics

## Cache backend

Cache values are disposable.

Changing cache backend does not require state migration.

## Rate-limit backend

Changing backend resets or separates counters unless a deliberate state
transfer is implemented.

The operational effect SHALL be understood.

## Transient-state backend

Existing temporary state may become unavailable after a switch.

Correctness-critical state SHALL not rely on an unplanned backend switch.

## Task backend

Queued tasks do not automatically move between backends.

Backend changes SHALL occur only when the previous queue is empty or its
remaining work is intentionally handled.

For the initial greenfield launch, no legacy production queue exists.

## Storage backend

Storage objects do not automatically move between providers.

The greenfield GCP launch starts with empty GCS buckets.

After real use begins, changing storage requires a separate migration plan.

---

# 58. Configuration Ownership

Each configuration group SHOULD have an owner.

Suggested ownership:

```text
Django security -> application maintainers
Cloud Run -> platform maintainers
Cloud SQL -> database/platform maintainers
storage -> application and platform maintainers
tasks -> application and platform maintainers
Redis -> platform maintainers
email -> application operations
secrets -> security/platform maintainers
```

Ownership MAY be held by the same person in a small deployment, but
responsibilities SHALL remain explicit.

---

# 59. Configuration Documentation Requirements

Each new variable SHALL document:

- name;
- purpose;
- whether required;
- whether secret;
- supported values;
- default;
- applicable roles;
- applicable environments;
- validation behavior;
- operational impact.

Undocumented production variables SHALL not be introduced casually.

---

# 60. Example API Service Configuration

Non-secret conceptual values:

```text
DJANGO_SETTINGS_MODULE=config.settings.deployment
CARE_ENVIRONMENT=prod
CARE_PROCESS_ROLE=api
DJANGO_DEBUG=false

CARE_STORAGE_BACKEND=gcs
CARE_TASK_BACKEND=cloud_tasks
CARE_CACHE_BACKEND=postgres
CARE_RATE_LIMIT_BACKEND=postgres
CARE_TRANSIENT_STATE_BACKEND=postgres
CARE_REPORT_PROGRESS_BACKEND=database_model

GCP_PROJECT_ID=care-production
GCP_REGION=us-central1
GCP_TASKS_LOCATION=us-central1
GCP_TASKS_QUEUE=care-default
GCP_WORKER_URL=https://care-prod-worker-...run.app/internal/tasks/execute/
GCP_TASKS_SERVICE_ACCOUNT=care-tasks-invoker@care-production.iam.gserviceaccount.com

CARE_PATIENT_STORAGE_BUCKET=care-prod-patient-files
CARE_FACILITY_STORAGE_BUCKET=care-prod-facility-files
CARE_REPORT_STORAGE_BUCKET=care-prod-reports

CARE_CACHE_TABLE=care_cache
CARE_LOG_FORMAT=json
CARE_LOG_LEVEL=INFO
```

Secrets:

```text
DJANGO_SECRET_KEY
DATABASE_URL
EMAIL_HOST_PASSWORD
JWKS_BASE64 or equivalent private material
SENTRY_DSN, when enabled
```

---

# 61. Example Worker Service Configuration

```text
DJANGO_SETTINGS_MODULE=config.settings.deployment
CARE_ENVIRONMENT=prod
CARE_PROCESS_ROLE=task_worker

CARE_STORAGE_BACKEND=gcs
CARE_TASK_BACKEND=cloud_tasks
CARE_CACHE_BACKEND=postgres
CARE_RATE_LIMIT_BACKEND=postgres
CARE_TRANSIENT_STATE_BACKEND=postgres
CARE_REPORT_PROGRESS_BACKEND=database_model

CARE_TASK_HANDLER_ENDPOINT_ENABLED=true
CARE_TASK_LOG_PAYLOAD=false

GCP_PROJECT_ID=care-production
GCP_REGION=us-central1

CARE_PATIENT_STORAGE_BUCKET=care-prod-patient-files
CARE_FACILITY_STORAGE_BUCKET=care-prod-facility-files
CARE_REPORT_STORAGE_BUCKET=care-prod-reports

CARE_LOG_FORMAT=json
CARE_LOG_LEVEL=INFO
```

The worker does not necessarily need queue-enqueue configuration unless tasks
can create follow-up tasks.

---

# 62. Example Migration Job Configuration

```text
DJANGO_SETTINGS_MODULE=config.settings.deployment
CARE_ENVIRONMENT=prod
CARE_PROCESS_ROLE=job
CARE_JOB_NAME=migrate

CARE_STORAGE_BACKEND=gcs
CARE_CACHE_BACKEND=postgres

GCP_PROJECT_ID=care-production
GCP_REGION=us-central1

CARE_LOG_FORMAT=json
CARE_LOG_LEVEL=INFO
```

The migration job may not require task-dispatch configuration.

The exact settings validation SHALL account for process role.

---

# 63. Definition of Configuration Completion

Configuration implementation is complete when:

- GCP settings load with explicit validated values;
- the default GCP profile starts without Redis;
- local Celery, Redis and MinIO remain supported;
- GCS storage aliases resolve;
- MinIO aliases resolve locally;
- Cloud Tasks variables are required only when selected;
- PostgreSQL cache variables are validated;
- optional Redis responsibilities use independent URLs;
- role-specific services receive only required configuration;
- production rejects insecure defaults;
- diagnostics redact secrets;
- tests cover supported profile combinations;
- configuration documentation matches implementation.

---

## 64. Next Document

The next document is:

```text
docs/xii/architecture/08-terraform-architecture.md
```

It will define:

- Terraform repository structure;
- environment composition;
- modules;
- APIs;
- service accounts;
- IAM;
- Cloud SQL;
- Cloud Storage;
- Artifact Registry;
- Cloud Run services;
- Cloud Run Jobs;
- Cloud Tasks;
- Cloud Scheduler;
- Secret Manager;
- monitoring;
- state management;
- outputs;
- resource-protection rules.
