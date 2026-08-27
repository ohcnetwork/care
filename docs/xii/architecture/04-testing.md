---
title: GCP Testing Strategy
document: 04-testing
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
---

# GCP Testing Strategy

## 1. Purpose

This document defines the testing strategy for the greenfield GCP adaptation of
CARE.

The test suite SHALL verify that:

- existing CARE behavior remains functional;
- local Docker Compose development remains supported;
- GCP settings are valid;
- Cloud Run services start correctly;
- Cloud SQL works with Django ORM;
- all file operations use Django Storage API;
- MinIO and GCS behave consistently for CARE use cases;
- uploads and downloads pass through Django;
- Cloud Tasks executes registered tasks securely;
- PostgreSQL can provide shared cache and state;
- Redis remains optional;
- optional Redis-compatible deployments work when enabled;
- an optional PostgreSQL task queue can be evaluated without weakening the
  default Cloud Tasks profile;
- upstream updates remain testable.

The strategy is designed for a new deployment.

It does not include:

- production-data migration tests;
- legacy-object copy verification;
- dual-write tests;
- coexistence with an existing production installation;
- cutover from a running legacy stack.

---

## 2. Testing Principles

### 2.1 Preserve upstream tests

The official CARE test suite SHALL remain the primary regression baseline.

GCP-specific tests SHALL extend the existing suite rather than replace it.

### 2.2 Test behavior, not implementation details

Tests SHOULD verify observable behavior.

Examples:

```text
file can be uploaded and downloaded
task is enqueued and executed
cache value is shared across processes
unauthorized worker invocation is rejected
```

Tests SHOULD avoid asserting unnecessary internal details such as:

- exact private method names;
- internal client construction;
- provider SDK object shapes;
- Terraform resource ordering.

### 2.3 Test supported deployment profiles

At minimum, tests SHALL cover:

```text
local upstream-compatible profile
GCP default profile
GCP PostgreSQL-cache profile
GCP optional Redis profile
```

The PostgreSQL queue profile SHALL be tested only if that backend is accepted.

### 2.4 Keep tests deterministic

Tests SHALL avoid:

- real patient data;
- uncontrolled external dependencies;
- arbitrary sleeps;
- dependence on previous test order;
- persistent shared state between runs;
- manually prepared cloud resources.

### 2.5 Separate test levels

The suite SHALL distinguish:

```text
unit tests
application integration tests
provider integration tests
container tests
infrastructure validation
deployment smoke tests
end-to-end tests
```

A failure should identify the responsible layer.

---

## 3. Test Categories

The project SHALL organize tests into the following categories.

```text
tests/
├── unit/
├── integration/
│   ├── storage/
│   ├── tasks/
│   ├── cache/
│   ├── database/
│   └── redis/
├── api/
│   └── files/
├── container/
├── gcp/
│   ├── cloud_run/
│   ├── cloud_tasks/
│   ├── cloud_sql/
│   └── cloud_storage/
├── security/
├── smoke/
└── upstream/
```

This structure is illustrative.

The implementation MAY follow existing CARE test conventions instead of
creating this exact directory layout.

The conceptual separation SHALL remain.

---

# 4. Upstream Regression Tests

## 4.1 Objective

Ensure GCP changes do not break ordinary CARE development.

## 4.2 Required commands

The official local workflow SHALL continue to run:

```bash
make build
make up
make load-fixtures
make test
```

or the current official equivalents.

The regression gate SHALL verify:

- PostgreSQL container starts;
- Redis container starts;
- MinIO container starts;
- backend container starts;
- Celery container starts;
- migrations succeed;
- fixtures load;
- official tests pass;
- no GCP credentials are required.

## 4.3 Local task verification

The local profile SHALL continue testing:

```text
Celery
Redis broker
Redis result backend
Celery Beat
```

GCP-specific changes SHALL not silently change local task behavior.

## 4.4 Local storage verification

Local tests SHALL verify that MinIO works through:

```text
django-storages
S3Storage
```

The tests SHALL no longer depend on CARE's direct `boto3` file manager after
the storage migration is complete.

## 4.5 Exit gate

No GCP feature branch SHALL merge if it breaks the supported local profile.

---

# 5. Settings Tests

## 5.1 Objective

Verify that settings modules construct valid configurations for each supported
profile.

## 5.2 GCP settings import

Test:

```bash
DJANGO_SETTINGS_MODULE=config.settings.deployment \
python manage.py check
```

with valid environment variables.

## 5.3 Missing configuration

Tests SHALL verify clear failures when required variables are absent.

Examples:

```text
DJANGO_SECRET_KEY
DATABASE_URL
GCP_PROJECT_ID
CARE_PATIENT_STORAGE_BUCKET
CARE_FACILITY_STORAGE_BUCKET
CARE_REPORT_STORAGE_BUCKET
GCP_TASKS_QUEUE
GCP_WORKER_URL
```

Only variables required by the selected backend SHALL be mandatory.

For example:

```text
REDIS_CACHE_URL
```

SHALL not be required when:

```text
CARE_CACHE_BACKEND=postgres
```

## 5.4 Invalid backend names

Tests SHALL reject values such as:

```text
CARE_TASK_BACKEND=unknown
CARE_CACHE_BACKEND=memcached-guess
CARE_RATE_LIMIT_BACKEND=invalid
```

The resulting error SHALL identify:

- the invalid variable;
- the invalid value;
- supported values.

## 5.5 Profile combinations

Test at least:

```text
cloud_tasks + postgres cache
cloud_tasks + redis cache
celery + redis cache
cloud_tasks + locmem cache
```

If accepted:

```text
postgres queue + postgres cache
```

## 5.6 Health-check construction

Verify that:

- Celery checks exist only when Celery is selected;
- Redis checks exist only when Redis is required;
- PostgreSQL cache checks exist when database cache is selected;
- GCP settings do not require Redis in the default profile.

---

# 6. Database Tests

## 6.1 Objective

Verify CARE works correctly with PostgreSQL and GCP-specific connection
settings.

## 6.2 Django ORM regression

The GCP adaptation SHALL reuse existing CARE ORM tests.

No separate persistence abstraction is required.

## 6.3 Migration tests

On an empty database, run:

```bash
python manage.py migrate --noinput
```

The command SHALL succeed from a clean schema.

The test SHALL detect:

- missing migrations;
- migration ordering issues;
- plugin migration failures;
- assumptions about pre-existing tables.

## 6.4 Setup commands

Verify from an empty database:

```bash
python manage.py sync_permissions_roles
python manage.py sync_valueset
```

Development tests MAY also run:

```bash
python manage.py load_fixtures
```

## 6.5 Cache-table creation

When PostgreSQL cache is selected, verify:

```bash
python manage.py createcachetable
```

creates the configured table.

The command SHOULD be idempotent or handled safely in deployment automation.

## 6.6 Connection tests

Container and GCP integration tests SHALL verify:

- initial connection;
- connection reuse;
- stale connection recovery;
- concurrent requests;
- maximum-instance connection budget;
- API and worker simultaneous access.

## 6.7 Transaction tests

Task dispatch tests SHALL verify:

```python
transaction.on_commit(...)
```

behavior where task creation depends on committed state.

A task SHALL not execute against data that was rolled back.

---

# 7. Django Storage Tests

## 7.1 Objective

Verify CARE uses Django Storage API consistently across MinIO and GCS.

## 7.2 Storage test matrix

The same logical test cases SHALL run against:

```text
S3Storage connected to MinIO
GoogleCloudStorage connected to GCS
```

A lightweight temporary filesystem backend MAY be used for fast unit tests, but
it SHALL not replace provider integration tests.

## 7.3 Alias tests

Verify that these aliases resolve:

```text
patient
facility
report
staticfiles
```

Each alias SHALL point to the expected backend in each environment.

## 7.4 Basic operations

Test:

```text
save
open
exists
delete
size
name normalization
streaming read
```

## 7.5 Object naming

Verify the expected naming convention:

```text
<file_type>/<internal_name>
```

Test:

- nested prefixes;
- Unicode;
- whitespace;
- long names;
- repeated names;
- extensions;
- generated internal names.

## 7.6 Duplicate names

Django Storage may modify a name when an object already exists.

Tests SHALL verify CARE's intended behavior for duplicate names.

If CARE requires stable object names, the implementation SHALL explicitly
delete, overwrite or generate unique names according to CARE semantics.

Tests SHALL not assume identical overwrite behavior across providers without
verification.

## 7.7 Content types

Verify that saved files preserve or expose the expected content type where
supported.

CARE responses SHALL not trust storage metadata without validation.

## 7.8 Missing objects

Verify behavior when:

- database record exists but object does not;
- object is deleted before download;
- storage raises a not-found error.

The API SHALL return a controlled CARE-level response rather than an unhandled
provider exception.

## 7.9 Permission failures

Simulate or test:

- read denied;
- write denied;
- delete denied;
- bucket missing.

Provider exceptions SHALL be handled consistently.

## 7.10 Provider isolation

Tests SHALL ensure CARE file code does not import:

```text
boto3
google.cloud.storage
```

outside approved dependency modules.

A static-analysis or import-boundary test MAY enforce this.

---

# 8. File Upload API Tests

## 8.1 Objective

Verify that all uploads pass through authenticated CARE endpoints.

## 8.2 Successful upload

Test:

1. authenticated request;
2. authorized user;
3. valid file;
4. storage save;
5. database record creation or update;
6. provider-neutral API response.

## 8.3 Authentication

Verify unauthenticated requests are rejected.

## 8.4 Authorization

Verify users cannot upload files for:

- unauthorized patients;
- unauthorized facilities;
- inaccessible encounters;
- other tenants or organizations.

Tests SHALL follow CARE's actual authorization model.

## 8.5 Extension validation

Test:

- allowed extensions;
- blocked executable extensions;
- missing extension;
- double extension;
- uppercase extension;
- misleading extension.

## 8.6 MIME validation

Test:

- allowed MIME type;
- mismatched MIME type;
- missing MIME type;
- unsafe MIME type;
- browser-provided incorrect MIME type.

The implementation SHOULD validate using more than the filename when current
CARE policy requires it.

## 8.7 File-size limits

Test:

- file below memory threshold;
- file above memory threshold but below maximum;
- file exactly at maximum;
- file above maximum;
- request above total upload limit.

## 8.8 Temporary upload handling

For files above the in-memory threshold, verify Django uses temporary-file
handling rather than loading the complete file into memory.

## 8.9 Storage failure

Simulate storage failure after request validation.

Verify:

- no false success response;
- database consistency;
- no completed record referencing a missing object;
- appropriate logging.

## 8.10 Database failure

Simulate database failure after storage write.

Verify the implementation performs its documented cleanup or leaves a
detectable incomplete object for cleanup.

## 8.11 Empty file

Test whether zero-byte files are:

- accepted;
- rejected;
- accepted only for selected types.

The behavior SHALL be explicit.

---

# 9. File Download API Tests

## 9.1 Objective

Verify that downloads pass through CARE authorization and streaming.

## 9.2 Successful download

Test:

- authenticated request;
- authorized access;
- storage object exists;
- streaming response;
- correct content type;
- correct content disposition;
- expected filename.

## 9.3 Authorization

Verify users cannot download files outside their permitted scope.

## 9.4 Inline versus attachment

Test CARE's policy for:

```text
images
PDF
audio
video
documents
unknown types
```

The API SHALL set safe headers independent of provider-generated URLs.

## 9.5 Filename safety

Test filenames containing:

- quotes;
- semicolons;
- newlines;
- non-ASCII characters;
- path separators;
- control characters.

The response SHALL prevent header injection and path traversal.

## 9.6 Streaming behavior

Verify that the response does not read the complete file into memory.

For provider integration tests, record memory behavior for representative file
sizes.

## 9.7 Range requests

If CARE or the frontend requires media seeking, test HTTP range behavior.

Range support SHALL not be assumed automatically.

If not supported in the initial implementation, the limitation SHALL be
documented.

## 9.8 Missing object

Verify a controlled response when the database record exists but the object is
missing.

## 9.9 Storage timeout

Simulate a slow or failed storage read.

Verify:

- request timeout behavior;
- controlled error response;
- logging without sensitive content.

---

# 10. Task Dispatch Unit Tests

## 10.1 Objective

Verify backend-neutral task dispatch behavior.

## 10.2 Common dispatch cases

Test:

```text
task name
JSON payload
delay
external task ID
configuration selection
serialization failure
backend failure
```

## 10.3 Payload restrictions

Reject or clearly fail for:

- model instances;
- querysets;
- file objects;
- unserializable objects;
- credentials;
- unexpected binary payloads.

## 10.4 Transaction behavior

Verify tasks scheduled through `transaction.on_commit` are:

- not dispatched before commit;
- dispatched after commit;
- not dispatched after rollback.

## 10.5 Unknown task

The dispatcher or handler registry SHALL reject unknown task names.

## 10.6 Backend selection

Verify:

```text
CARE_TASK_BACKEND=celery
CARE_TASK_BACKEND=cloud_tasks
```

and, if accepted:

```text
CARE_TASK_BACKEND=postgres
```

select the expected implementation.

---

# 11. Celery Compatibility Tests

## 11.1 Objective

Ensure local and traditional deployments continue working.

## 11.2 Existing tasks

Test existing wrappers for:

```text
cleanup_expired_token_slots
cleanup_incomplete_file_uploads
generate_report_task
send_totp_enabled_email
send_totp_disabled_email
```

## 11.3 Reusable logic

Verify Celery wrappers invoke the same reusable functions used by other
backends.

## 11.4 Retry behavior

Verify task-specific retry behavior remains compatible.

## 11.5 Periodic registration

Verify local Celery Beat registers the expected schedules.

## 11.6 Result compatibility

Where existing call sites use Celery task IDs or results, test that local
behavior remains unchanged until those call sites are deliberately refactored.

---

# 12. Cloud Tasks Unit Tests

## 12.1 Objective

Verify Cloud Tasks request construction without requiring a real GCP queue.

## 12.2 Client mocking

Mock the official Cloud Tasks client.

Verify:

- parent queue path;
- HTTP method;
- worker URL;
- JSON body;
- content type;
- OIDC service account;
- OIDC audience;
- schedule time;
- generated task name.

## 12.3 Delay

Test:

- no delay;
- positive delay;
- invalid negative delay;
- maximum supported delay according to project policy.

## 12.4 Deterministic names

If task IDs are used for deduplication, test:

- valid name conversion;
- duplicate-name response;
- unsafe characters;
- length limits.

## 12.5 Sensitive logging

Verify task payloads are not fully logged.

---

# 13. Cloud Tasks Worker Tests

## 13.1 Objective

Verify the private HTTP worker safely executes registered handlers.

## 13.2 Method validation

Only POST SHALL be accepted.

## 13.3 Content-type validation

Invalid content types SHALL be rejected.

## 13.4 Authentication boundary

Application tests MAY simulate authenticated and unauthenticated requests.

Deployment smoke tests SHALL verify actual Cloud Run IAM behavior.

## 13.5 Handler registry

Test:

- known task;
- unknown task;
- malformed task name;
- missing payload;
- invalid payload;
- extra fields.

## 13.6 Arbitrary execution protection

Verify a request cannot execute:

- arbitrary Python paths;
- imported modules;
- `eval`;
- shell commands;
- unregistered callables.

## 13.7 Success response

A handler that completes successfully SHALL return a 2xx response.

## 13.8 Transient failure

A retriable exception SHALL produce a response that allows Cloud Tasks retry.

## 13.9 Permanent failure

A permanent validation or business error SHALL follow a defined non-retry or
limited-retry policy.

## 13.10 Retry metadata

Test parsing and logging of Cloud Tasks metadata headers when present.

The headers SHALL not replace IAM authentication.

---

# 14. Task Idempotency Tests

## 14.1 Objective

Ensure retries and duplicate delivery do not corrupt CARE state.

## 14.2 Email tasks

Test duplicate execution behavior.

The project SHALL decide whether duplicate security-notification emails are:

- acceptable;
- suppressed through idempotency;
- limited through task identity.

## 14.3 Report generation

Test repeated execution using the same logical request.

Verify:

- duplicate records are prevented or intentional;
- object names remain consistent with policy;
- partial previous attempts are handled;
- progress state is updated correctly.

## 14.4 Cleanup tasks

Execute cleanup commands repeatedly.

The second execution SHALL succeed with no remaining matching records.

## 14.5 Task execution records

If an idempotency or execution table is introduced, test:

- first claim;
- duplicate claim;
- completed task;
- failed task;
- retry;
- stale execution;
- concurrent requests.

---

# 15. Cloud Run Job Tests

## 15.1 Objective

Verify administrative and scheduled commands can run as one-off jobs.

## 15.2 Management commands

Test:

```text
migrate
sync_permissions_roles
sync_valueset
cleanup_expired_token_slots
cleanup_incomplete_file_uploads
```

## 15.3 Empty-state behavior

On an empty database and empty buckets:

- cleanup commands SHALL succeed;
- synchronization commands SHALL complete;
- commands SHALL not assume existing patients or files.

## 15.4 Exit codes

Successful jobs SHALL return exit code zero.

Failures SHALL return non-zero.

## 15.5 Repeated execution

Management commands intended for scheduled use SHALL be safe to execute
repeatedly.

## 15.6 Job timeout

Long-running behavior SHALL be tested against configured Cloud Run Job limits.

---

# 16. Cloud Scheduler Tests

## 16.1 Objective

Verify scheduled definitions correspond to intended CARE behavior.

## 16.2 Configuration validation

Terraform tests SHALL verify:

- schedule expression;
- timezone;
- target job or queue;
- authentication;
- retry policy;
- enabled state.

## 16.3 Schedule mapping

Verify:

```text
expired token cleanup -> daily
incomplete upload cleanup -> configured cadence
```

## 16.4 Duplicate scheduling

The GCP profile SHALL not start Celery Beat.

A configuration test SHALL prevent both:

```text
Cloud Scheduler
Celery Beat
```

from being enabled for the same environment unless explicitly intended.

---

# 17. PostgreSQL Cache Tests

## 17.1 Objective

Verify Django's database cache works as shared cache across instances.

## 17.2 Basic cache operations

Test:

```text
set
get
add
delete
clear
timeout
expiration
get_many
set_many
```

Only operations actually required by CARE must be treated as mandatory.

## 17.3 Cross-process visibility

Use two separate Django processes or database connections.

Verify a value written by one is visible to the other.

## 17.4 Expiration

Verify expired entries are treated as missing.

The suite SHOULD also observe whether expired rows are removed according to
Django's database-cache behavior.

## 17.5 Culling

Configure a small maximum-entry count in a dedicated test.

Verify culling does not produce application errors.

## 17.6 Report progress

Test progress updates through PostgreSQL cache:

```text
initial value
progress update
read from another process
expiration
clear
```

## 17.7 Database failure

Verify application behavior when the cache table is unavailable.

The expected behavior SHALL be explicit.

For example:

```text
performance cache -> controlled miss or error policy
report progress -> controlled temporary failure
```

## 17.8 Query volume

Performance tests SHALL measure database queries generated by cache use.

The project SHALL identify endpoints where database-backed cache creates more
load than the uncached operation.

---

# 18. PostgreSQL Rate-Limit Tests

## 18.1 Objective

Verify globally consistent limits across Cloud Run instances.

## 18.2 Shared enforcement

Simulate requests from separate application processes.

Verify they contribute to the same limit.

## 18.3 Concurrent requests

Test simultaneous requests around the threshold.

The implementation SHALL not allow excessive requests due to lost updates.

## 18.4 Key dimensions

Test limits based on the dimensions actually used by CARE, such as:

```text
user
IP
endpoint
operation
facility
```

## 18.5 Window expiration

Verify counters reset or expire as expected.

## 18.6 Failure policy

Test behavior during database errors.

Security-sensitive limits SHALL have a documented fallback.

---

# 19. PostgreSQL Transient-State Tests

## 19.1 Objective

Verify shared short-lived state stored in PostgreSQL behaves correctly.

## 19.2 Explicit models

For correctness-sensitive state, test:

- creation;
- expiration;
- concurrent update;
- cleanup;
- audit fields;
- uniqueness.

## 19.3 Cache-backed state

For disposable state, reuse PostgreSQL cache tests.

## 19.4 Cleanup

Expired state SHALL be removable without affecting active records.

---

# 20. Optional PostgreSQL Queue Tests

This section applies only if the PostgreSQL task backend is accepted.

## 20.1 Objective

Verify reliable queue behavior without claiming serverless equivalence to Cloud
Tasks.

## 20.2 Schema creation

Test queue schema creation from an empty database.

## 20.3 Enqueue and claim

Test:

- enqueue;
- single-worker claim;
- competing workers;
- no double claim;
- completion.

## 20.4 Transactional enqueue

Verify a queued task:

- exists after transaction commit;
- does not exist after rollback.

## 20.5 Retry

Test:

- transient failure;
- retry count;
- delay;
- terminal failure.

## 20.6 Worker restart

Verify jobs remain available after worker termination.

## 20.7 Queue cleanup

Test retention and removal of completed or failed jobs.

## 20.8 Database pressure

Measure:

- connections;
- polling queries;
- notification behavior;
- queue-table growth;
- impact on CARE queries.

## 20.9 Worker freshness

Health checks SHALL detect an inactive or stale worker.

---

# 21. Redis Compatibility Tests

## 21.1 Objective

Verify Redis can be enabled selectively and remains optional.

## 21.2 Supported configurations

Test:

```text
Redis cache only
Redis rate limiting only
Redis transient state only
Celery + Redis
```

## 21.3 TLS

For providers such as Upstash, test:

```text
rediss://
certificate verification
connection timeout
authentication
```

## 21.4 Command compatibility

Test only commands actually required by CARE.

Do not assume complete Redis command or module compatibility.

## 21.5 Outage behavior

Simulate Redis unavailability.

Verify documented behavior for:

```text
cache
rate limiting
progress
Celery broker
```

## 21.6 Redis-free startup

The most important negative test is:

```text
CARE starts and serves requests without any Redis URL
```

for the default GCP profile.

---

# 22. Container Tests

## 22.1 Objective

Verify the production image works before cloud deployment.

## 22.2 Image build

The image SHALL build from a clean checkout.

## 22.3 No secrets

Inspect image layers and environment defaults for:

- credentials;
- `.env` files;
- service-account JSON;
- database passwords;
- private keys.

## 22.4 Runtime user

Verify the process runs as the intended non-root user when configured.

## 22.5 API startup

Start the image locally with:

```text
CARE_PROCESS_ROLE=api
```

Verify Gunicorn listens on `$PORT`.

## 22.6 Worker startup

Start the image in task-worker mode.

Verify the internal task endpoint is reachable locally.

## 22.7 Job command

Run a management command using the same image.

## 22.8 Static files

Verify collected static assets are included and served.

## 22.9 Redis-free image startup

Start the GCP profile without Redis.

No startup script SHALL wait for Redis.

---

# 23. Terraform Tests

## 23.1 Objective

Verify infrastructure configuration before application deployment.

## 23.2 Formatting and validation

`terraform fmt` and `terraform validate` both act on a single directory.
`fmt` therefore needs `-recursive` to reach `modules/` and `environments/`, and
`validate` needs one invocation per initialized directory — there is no
recursive form.

From `deploy/gcp/terraform/` (layout: 03-migration-plan.md §29):

```bash
terraform fmt -check -recursive .

for dir in environments/*/; do
  terraform -chdir="$dir" init -backend=false
  terraform -chdir="$dir" validate
done
```

Modules are validated through the environments that instantiate them. A module
that no environment references SHALL be validated on its own the same way.

## 23.3 Plan review

CI SHALL generate a plan for approved environments.

The plan SHALL be reviewable before apply.

## 23.4 Policy tests

Verify:

- buckets are private;
- worker disallows unauthenticated access;
- service accounts do not receive Owner or Editor;
- Cloud SQL is not unrestricted publicly;
- minimum instances follow environment policy;
- secrets are not stored as plain Terraform variables where avoidable;
- task invoker can invoke only the worker.

## 23.5 Environment separation

Verify development, staging and production names do not collide.

## 23.6 Destructive changes

CI SHOULD highlight:

- Cloud SQL replacement;
- bucket deletion;
- secret deletion;
- service-account replacement;
- task-queue deletion.

---

# 24. Cloud Run Deployment Smoke Tests

## 24.1 Objective

Verify the deployed development or staging environment works.

## 24.2 API health

Test the public or authenticated health endpoint.

## 24.3 Database

Execute a safe database-backed request.

## 24.4 Static files

Request a known static asset.

## 24.5 File flow

Using synthetic data:

1. upload a small file through CARE;
2. confirm the record exists;
3. download it through CARE;
4. compare content;
5. delete it;
6. verify subsequent access fails.

## 24.6 Task flow

1. enqueue a test-safe task;
2. confirm worker invocation;
3. confirm expected database or email-test result;
4. verify task logs contain the task ID;
5. verify no sensitive payload is logged.

## 24.7 Scale from zero

After allowing services to scale down, invoke:

```text
API
worker task
```

and verify cold-start behavior remains within acceptable limits.

## 24.8 Unauthorized worker call

Call the worker without valid IAM identity.

The request SHALL fail.

## 24.9 Scheduled job

Invoke one scheduled job manually and verify successful completion.

---

# 25. Empty-State Tests

## 25.1 Objective

Verify a completely new CARE installation works before data exists.

## 25.2 Empty database

Test:

- initial API behavior;
- admin setup;
- first facility creation;
- first user creation;
- first patient creation;
- list endpoints returning empty collections.

## 25.3 Empty buckets

Test:

- no failures when buckets contain no objects;
- cleanup jobs succeed;
- missing-file responses remain controlled.

## 25.4 Initial value sets

Verify setup commands populate required value sets from an empty database.

## 25.5 Initial permissions

Verify permission synchronization produces expected roles and permissions.

## 25.6 First report

Test report behavior before and after required templates are created.

## 25.7 First scheduled execution

Periodic cleanup SHALL succeed before any matching data exists.

---

# 26. Security Tests

## 26.1 Objective

Verify the GCP adaptation does not weaken CARE security.

## 26.2 File access

Test horizontal and vertical authorization for files.

## 26.3 Path traversal

Attempt object names or filenames containing:

```text
../
absolute paths
encoded traversal
backslashes
```

Storage-relative names SHALL remain safe.

## 26.4 Malicious filenames

Test response-header injection and unsafe characters.

## 26.5 Oversized requests

Verify large requests are rejected before exhausting instance resources.

## 26.6 Worker authentication

Verify Cloud Run IAM protects the worker independently of application headers.

## 26.7 Task-name injection

Attempt arbitrary handler execution.

## 26.8 Secret exposure

Inspect:

- logs;
- error responses;
- task payloads;
- environment output;
- health endpoints.

Secrets SHALL not be exposed.

## 26.9 Bucket access

Verify buckets are not anonymously readable or writable.

## 26.10 Service-account privilege

Review effective IAM permissions.

No runtime service account SHALL have project-wide Owner or Editor.

## 26.11 Database exposure

Verify Cloud SQL is not openly reachable from unrestricted networks.

---

# 27. Performance Tests

## 27.1 Objective

Verify the low-cost architecture remains usable.

## 27.2 API latency

Measure representative CARE requests under:

```text
warm instance
cold start
moderate concurrency
```

## 27.3 File upload

Measure:

- duration;
- memory;
- CPU;
- temporary-disk use;
- Cloud Run timeout margin.

Use representative supported sizes.

## 27.4 File download

Measure:

- first-byte latency;
- throughput;
- memory;
- concurrent streams.

## 27.5 PostgreSQL cache

Measure:

- cache read latency;
- cache write latency;
- queries per request;
- impact on application transactions.

## 27.6 Rate limiting

Measure counter update overhead under concurrent requests.

## 27.7 Cloud Tasks

Measure:

- enqueue latency;
- queue-to-start latency;
- cold worker start;
- execution time.

## 27.8 Database connections

Measure active connections during:

- API concurrency;
- worker concurrency;
- jobs;
- database cache use.

## 27.9 Acceptance thresholds

Thresholds SHALL be documented after the initial benchmark.

The project SHALL not invent arbitrary guarantees before measurement.

---

# 28. Failure and Recovery Tests

## 28.1 Cloud SQL interruption

Verify:

- controlled request failure;
- connection recovery;
- no corrupted state;
- health-check response.

## 28.2 Cloud Storage denial

Verify upload and download failures are controlled.

## 28.3 Cloud Tasks enqueue failure

Verify the API does not falsely report successful task creation.

## 28.4 Worker failure

Verify Cloud Tasks retries according to policy.

## 28.5 Duplicate task

Verify idempotency.

## 28.6 Email failure

Verify retry and terminal failure behavior.

## 28.7 PostgreSQL cache table missing

Verify startup or health diagnostics identify the problem clearly.

## 28.8 Redis outage

When Redis is optional, verify unrelated functionality continues when
appropriate.

## 28.9 Cloud Run Job failure

Verify non-zero exit status and alerting.

---

# 29. Plugin Compatibility Tests

## 29.1 Objective

Verify required CARE plugins do not depend on removed behavior.

## 29.2 Inventory

For each required plugin, inspect:

- Celery tasks;
- Redis use;
- `boto3`;
- signed URLs;
- custom file managers;
- health checks;
- startup hooks;
- migrations.

## 29.3 Storage

Required plugins SHALL either:

- use Django Storage API;
- remain compatible with the selected storage profile;
- be explicitly unsupported.

## 29.4 Tasks

Plugin tasks SHALL be classified as:

```text
Cloud Tasks compatible
Cloud Run Job compatible
Celery-only
unsupported
```

## 29.5 Test gate

A plugin SHALL not be enabled in production until its required runtime behavior
has been tested.

---

# 30. CI Test Stages

The CI pipeline SHOULD use stages similar to:

```text
Stage 1: formatting and lint
Stage 2: unit tests
Stage 3: Django application tests
Stage 4: PostgreSQL integration
Stage 5: MinIO storage integration
Stage 6: Redis compatibility
Stage 7: container build and tests
Stage 8: Terraform validation
Stage 9: optional deployed-environment smoke tests
```

GCS and Cloud Tasks live integration tests MAY run:

- on protected branches;
- nightly;
- before release;
- against an isolated development project.

They need not run for every untrusted pull request if credentials would be
exposed.

---

# 31. Test Data Policy

Tests SHALL use synthetic data.

Production patient data SHALL not be used.

Test fixtures SHALL avoid:

- real names;
- real clinical records;
- real contact information;
- real identifiers.

Uploaded test files SHALL contain synthetic or empty sample content.

---

# 32. Test Isolation

Each test run SHOULD use isolated:

```text
database schema or database
storage prefix or bucket
task queue
cache namespace
```

Cloud integration tests SHALL clean up resources they create.

Cleanup failure SHALL be reported.

---

# 33. Test Configuration

Test settings SHOULD provide backend overrides.

Examples:

```text
CARE_TASK_BACKEND=fake
CARE_CACHE_BACKEND=dummy
```

for fast unit tests.

`fake` is a **test-only** value. The production backend contract accepts
`cloud_tasks`, `celery` and `postgres` only, and production settings SHALL
reject `fake` at startup rather than silently discarding every task. It is
listed here because test settings are the one place it is permitted.

Integration suites SHALL deliberately select:

```text
celery
cloud_tasks
postgres
redis
```

as applicable.

A fake backend SHALL not replace real integration testing.

---

# 34. Coverage Expectations

Coverage SHALL prioritize:

- storage flows;
- authentication and authorization;
- task dispatch;
- task handlers;
- idempotency;
- cache selection;
- Redis optionality;
- settings validation;
- management commands;
- health checks.

A single global coverage percentage SHALL not be treated as proof of adequate
testing.

Critical migration paths SHALL have explicit tests.

---

# 35. Release Gates

A GCP release SHALL require:

- upstream CARE tests pass;
- GCP settings tests pass;
- production image builds;
- Terraform validates;
- storage tests pass;
- file API security tests pass;
- task dispatcher tests pass;
- Cloud Tasks worker tests pass;
- PostgreSQL cache tests pass;
- Redis-free startup passes;
- deployed smoke tests pass in staging;
- no critical security findings remain.

If the PostgreSQL queue is supported, its queue tests SHALL also pass for
profiles that use it.

---

# 36. Upstream Synchronization Gates

After merging a new upstream version, run:

```text
local regression suite
storage integration suite
task suite
PostgreSQL cache suite
container build
Terraform validation
GCP smoke tests
```

Special review SHALL focus on upstream changes to:

```text
settings
tasks
file models
file endpoints
Dockerfiles
startup scripts
health checks
plugins
```

---

# 37. Test Deliverables

The implementation SHALL produce:

```text
documented test commands
profile-specific test configuration
storage integration tests
file API tests
task dispatch tests
Cloud Tasks worker tests
task idempotency tests
PostgreSQL cache tests
rate-limit tests
optional Redis tests
container tests
Terraform validation
Cloud Run smoke tests
empty-state tests
security tests
upstream regression gates
```

---

# 38. Definition of Testing Completion

Testing for the initial GCP implementation is complete when:

- a clean local checkout passes the supported local workflow;
- CARE starts with GCP settings and no Redis;
- an empty Cloud SQL database initializes successfully;
- MinIO and GCS pass required storage tests;
- all production file traffic passes through tested Django endpoints;
- unauthorized file access is rejected;
- Cloud Tasks dispatch and private worker execution pass;
- duplicate task delivery is safe;
- Cloud Scheduler and Jobs execute successfully;
- PostgreSQL cache works across instances;
- rate limiting is shared and concurrency-safe;
- optional Redis works when enabled;
- the production image passes container tests;
- Terraform passes validation and policy checks;
- staging smoke tests pass from an empty environment;
- upstream synchronization runs the complete regression gate.

---

## 39. Next Document

The next document is:

```text
docs/xii/architecture/05-upstream-sync.md
```

It will define:

- remote and branch configuration;
- upstream update workflow;
- conflict-resolution rules;
- recurring-conflict analysis;
- test requirements after synchronization;
- rules for keeping `develop` clean;
- rules for maintaining the `gcp` branch;
- release tagging and rollback references.
