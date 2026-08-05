---
title: GCP Operations Guide
document: 06-operations
version: 0.1.0
status: Draft
source_repository: https://github.com/ohcnetwork/care
target_platform: Google Cloud Platform
deployment_type: Greenfield
depends_on:
  - docs/gcp/00-scope-and-goals.md
  - docs/gcp/01-current-runtime.md
  - docs/gcp/02-target-runtime.md
  - docs/gcp/03-migration-plan.md
  - docs/gcp/04-testing.md
  - docs/gcp/05-upstream-sync.md
---

# GCP Operations Guide

## 1. Purpose

This document defines how to create, deploy, operate, observe, maintain and
recover a greenfield CARE environment on Google Cloud Platform.

It covers the operational lifecycle after the architecture and implementation
described in the preceding documents have been completed.

The guide assumes:

- CARE runs on Cloud Run;
- PostgreSQL runs on Cloud SQL;
- files use Django Storage API and Cloud Storage;
- asynchronous work uses Cloud Tasks by default;
- task execution occurs in a private Cloud Run service;
- periodic work uses Cloud Scheduler and Cloud Run Jobs;
- PostgreSQL may provide cache, rate limiting and transient state;
- Redis-compatible services remain optional;
- infrastructure is managed using Terraform;
- the same application image supports API, worker and job roles.

This guide does not describe the original Docker Compose runtime except where
it is used for local development or troubleshooting.

---

# 2. Operational Objectives

Operations SHALL prioritize:

1. patient-data protection;
2. correctness;
3. recoverability;
4. service availability;
5. observability;
6. upstream maintainability;
7. predictable cost;
8. operational simplicity.

Cost reductions SHALL not disable:

- database backups;
- access controls;
- required logs;
- recovery procedures;
- application health checks.

---

# 3. Environments

The supported environments SHOULD be:

```text
dev
staging
prod
```

Each environment SHOULD have separate:

- Cloud Run services;
- Cloud Run Jobs;
- Cloud SQL database or instance;
- Cloud Storage buckets;
- Cloud Tasks queues;
- Cloud Scheduler jobs;
- secrets;
- service-account identities;
- monitoring labels;
- deployment history.

Production data SHALL NOT be copied into development or staging without an
approved anonymization process.

---

# 4. Naming Convention

Resources SHOULD follow a predictable naming convention.

Example:

```text
care-<environment>-<resource>
```

Examples:

```text
care-dev-api
care-dev-worker
care-dev-migrate
care-dev-cleanup-files
care-dev-tasks
care-dev-patient-files
care-dev-facility-files
care-dev-reports
care-dev-db
```

Production examples:

```text
care-prod-api
care-prod-worker
care-prod-migrate
care-prod-tasks
```

Names SHOULD identify:

- application;
- environment;
- role.

Names SHOULD NOT contain:

- patient information;
- organization secrets;
- credentials;
- temporary developer names in production.

---

# 5. Resource Labels

All supported GCP resources SHOULD use labels or annotations containing:

```text
application=care
environment=dev|staging|prod
managed_by=terraform
component=api|worker|database|storage|tasks|jobs
```

Deployed Cloud Run revisions SHOULD also expose:

```text
APP_VERSION
GIT_COMMIT_SHA
UPSTREAM_COMMIT_SHA
DEPLOYED_AT
```

These values improve:

- log filtering;
- cost analysis;
- incident investigation;
- release traceability.

---

# 6. Initial Project Preparation

Before creating CARE infrastructure:

1. Select or create the GCP project.
2. Configure billing.
3. establish administrative ownership;
4. configure Terraform state storage;
5. configure deployment identity;
6. determine the primary region;
7. determine data-location requirements;
8. define environment naming;
9. define backup and retention requirements;
10. define production access procedures.

The primary region SHOULD be selected deliberately.

The API, worker, Cloud SQL, Cloud Storage and task queue SHOULD normally be
placed in compatible nearby locations to reduce:

- latency;
- network cost;
- operational complexity.

---

# 7. Required APIs

Terraform SHOULD enable only the APIs required by the deployment.

The expected set includes APIs for:

```text
Cloud Run
Cloud SQL
Cloud Storage
Cloud Tasks
Cloud Scheduler
Artifact Registry
Secret Manager
Cloud Logging
Cloud Monitoring
IAM
service networking where required
```

The exact API identifiers SHALL live in Terraform rather than this operational
document.

API enablement SHALL be reproducible.

Operators SHOULD NOT rely on manually enabled APIs that are absent from
infrastructure code.

---

# 8. Terraform State

Terraform state SHALL be stored remotely.

The state backend SHALL:

- restrict access;
- enable versioning where supported;
- prevent anonymous access;
- separate environments;
- support recovery of previous state versions;
- avoid storage in developer laptops as the authoritative copy.

Recommended conceptual separation:

```text
terraform-state/
├── dev/
├── staging/
└── prod/
```

Production Terraform access SHALL be more restrictive than development access.

The Terraform state may contain sensitive infrastructure metadata.

It SHALL be treated as confidential.

---

# 9. Terraform Workflow

The normal workflow is:

```bash
terraform fmt -check
terraform init
terraform validate
terraform plan
terraform apply
```

Production changes SHOULD use a reviewed plan.

The reviewed plan SHALL correspond to the exact code later applied.

Operators SHALL inspect plans for:

- Cloud SQL replacement;
- bucket deletion;
- service-account replacement;
- secret deletion;
- Cloud Run service recreation;
- queue deletion;
- IAM broadening;
- network changes.

Destructive stateful changes SHALL not be applied casually.

---

# 10. Environment Creation Order

A new environment SHOULD be created in this order:

1. project APIs;
2. Artifact Registry;
3. service accounts;
4. Secret Manager resources;
5. networking;
6. Cloud SQL;
7. Cloud Storage buckets;
8. Cloud Tasks queues;
9. container image;
10. Cloud Run Jobs;
11. database initialization;
12. worker service;
13. API service;
14. Cloud Scheduler;
15. smoke tests;
16. alerts and dashboards.

The exact Terraform dependency graph MAY automate much of this order.

Application initialization SHALL still remain explicit.

---

# 11. Service Accounts

The recommended service accounts are:

```text
care-api
care-worker
care-jobs
care-tasks-invoker
care-deployer
```

A smaller development environment MAY consolidate identities temporarily.

Production SHOULD keep responsibilities separate.

---

# 12. API Service Account

The API identity SHOULD receive only permissions required to:

- connect to Cloud SQL;
- read required secrets;
- read and write configured CARE buckets;
- enqueue Cloud Tasks;
- emit logs and metrics;
- call explicitly required external services.

The API identity SHALL NOT receive:

- project Owner;
- project Editor;
- unrestricted IAM administration;
- permission to invoke unrelated Cloud Run services;
- access to unrelated buckets;
- access to every secret in the project.

---

# 13. Worker Service Account

The worker identity SHOULD receive only permissions required to:

- connect to Cloud SQL;
- read required secrets;
- read and write configured CARE buckets;
- emit logs and metrics;
- call required email or external services.

The worker ordinarily does not need permission to create Cloud Tasks unless
handlers enqueue follow-up tasks.

Such permission SHALL be added only if a concrete workflow requires it.

---

# 14. Jobs Service Account

The jobs identity SHOULD receive permissions needed by administrative commands.

These may include:

- Cloud SQL connectivity;
- Cloud Storage access;
- secret access;
- logging;
- selected task enqueue permissions.

Migration jobs do not automatically require full bucket access.

Permissions SHOULD be tailored to the actual commands executed.

---

# 15. Task Invoker Service Account

The task invoker identity SHALL be used by Cloud Tasks to call the private
worker.

It SHOULD receive:

```text
Cloud Run invocation permission
```

only on the CARE worker service.

It SHALL not receive broad API, database or bucket permissions merely because
it invokes the worker.

The worker's own service account performs the actual work.

---

# 16. Deployment Service Account

The deployment identity MAY receive permissions to:

- push images;
- deploy Cloud Run services;
- update jobs;
- execute migration jobs;
- manage Scheduler;
- update task queues;
- update approved secrets or secret references;
- apply Terraform in approved environments.

Production deployment access SHOULD be limited to:

- CI/CD;
- authorized maintainers;
- emergency operational procedures.

---

# 17. Secret Management

Secrets SHALL be stored in Secret Manager or an equivalent protected mechanism.

Expected secrets include:

```text
DJANGO_SECRET_KEY
database password or connection secret
SMTP credentials
JWT or JWKS private material
Sentry DSN
external API credentials
optional Redis URLs
```

Non-secret configuration SHOULD remain ordinary environment variables.

Examples of non-secret values:

```text
GCP_PROJECT_ID
GCP_REGION
CARE_TASK_BACKEND
CARE_CACHE_BACKEND
bucket names
queue names
service URLs
```

---

# 18. Secret Versioning

Secret updates SHOULD create new versions rather than overwrite undocumented
values.

Operators SHALL know:

- which Cloud Run revision uses which secret reference;
- whether the service references a fixed version or latest version;
- whether a new service revision is required after rotation;
- how to roll back to a previous secret version.

Secret rotation SHALL be tested in staging before production where practical.

---

# 19. Forbidden Secret Practices

Operators SHALL NOT:

- commit `.env` production files;
- commit service-account JSON keys;
- paste secrets into issue trackers;
- expose secrets through Terraform outputs;
- print secrets in CI logs;
- include credentials in container images;
- store plaintext secrets in documentation;
- use patient information as secret names.

---

# 20. Artifact Registry

Artifact Registry SHALL store CARE container images.

Images SHOULD use immutable tags:

```text
<git-commit-sha>
<release-tag>
```

Example:

```text
care-api:3f49b8a
care-api:gcp-v2026.08.05.1
```

Deployments SHOULD record the image digest.

The same image SHOULD be used for:

```text
API
Cloud Tasks worker
Cloud Run Jobs
optional PostgreSQL queue worker
Celery worker in compatible deployments
```

---

# 21. Image Build

The production image build SHALL:

1. install locked dependencies;
2. compile translations;
3. collect static files;
4. exclude development-only tools;
5. exclude local `.env` files;
6. exclude Git credentials;
7. avoid embedded secrets;
8. produce deterministic metadata;
9. identify the upstream and GCP commits;
10. pass container tests.

A failed test SHALL prevent image promotion.

---

# 22. Image Retention

Artifact Registry retention SHOULD balance:

- rollback requirements;
- audit requirements;
- storage cost.

At minimum, operators SHOULD retain:

- the current production image;
- the previous known-good image;
- recent release images;
- images referenced by active revisions;
- images required for incident investigation.

Untagged temporary images MAY be cleaned automatically after a defined period.

Active revision images SHALL not be deleted.

---

# 23. Cloud SQL Creation

Cloud SQL SHALL be created through Terraform.

Initial configuration SHALL define:

- PostgreSQL version;
- region;
- machine size;
- storage size;
- storage growth policy;
- backup schedule;
- point-in-time recovery policy;
- maintenance window;
- deletion protection;
- network access;
- database name;
- application user.

The smallest development configuration MAY be used initially.

Production sizing SHALL be based on measured load.

---

# 24. Database Initialization

For a new environment:

1. create Cloud SQL;
2. create the CARE database;
3. create the CARE application user;
4. store the database credentials;
5. build and publish the application image;
6. create or update the migration job;
7. run Django migrations;
8. create cache tables if selected;
9. run required synchronization commands;
10. verify database health.

Expected commands include:

```bash
python manage.py migrate --noinput
python manage.py createcachetable
python manage.py sync_permissions_roles
python manage.py sync_valueset
```

`createcachetable` SHALL run only when the database cache backend is selected.

---

# 25. Fixture Loading

Fixtures MAY be loaded in:

```text
development
staging
demonstration environments
```

Production fixture loading SHALL be intentional.

Operators SHALL know whether fixtures:

- create sample users;
- create sample facilities;
- create clinical sample data;
- modify value sets;
- conflict with real initialization.

Synthetic fixtures SHALL not be mistaken for production data.

---

# 26. Database Connection Budget

Operators SHALL maintain a connection budget.

The maximum theoretical application connections are influenced by:

```text
API maximum instances
API workers per instance
worker maximum instances
worker process count
jobs
optional PostgreSQL queue workers
database-cache traffic
administrative connections
```

The configured maximum instances SHALL remain conservative until measured.

A connection-budget document SHOULD record:

```text
Cloud SQL connection capacity
reserved administrative headroom
API allocation
worker allocation
jobs allocation
monitoring allocation
```

---

# 27. Database Connection Exhaustion

Signs include:

- failed requests;
- worker task failures;
- elevated database connection count;
- connection timeout messages;
- job failures;
- readiness-check failures.

Immediate actions MAY include:

1. reduce Cloud Run maximum instances;
2. reduce Gunicorn worker count;
3. reduce worker concurrency;
4. inspect long-running queries;
5. inspect leaked or idle connections;
6. temporarily disable nonessential jobs;
7. increase database capacity when justified.

Operators SHALL not solve every connection problem by increasing Cloud SQL size
without investigating application concurrency.

---

# 28. Database Backups

Production SHALL enable automated Cloud SQL backups.

The backup policy SHALL define:

- schedule;
- retention;
- point-in-time recovery;
- restore testing cadence;
- responsible owner;
- incident escalation.

A backup that has never been restored in a test environment is not sufficient
evidence of recoverability.

---

# 29. Restore Testing

A restore test SHOULD periodically:

1. create an isolated database environment;
2. restore from a selected backup or recovery point;
3. connect a non-production CARE revision;
4. run `manage.py check`;
5. verify representative records;
6. verify migrations;
7. verify application startup;
8. destroy the temporary environment after approval.

Restore tests SHALL not expose production data to unauthorized environments.

---

# 30. Database Maintenance

Operators SHOULD monitor:

- CPU;
- memory;
- disk utilization;
- storage growth;
- connection count;
- transaction duration;
- slow queries;
- locks;
- table growth;
- cache-table growth;
- task-state growth;
- queue-table growth if enabled.

PostgreSQL infrastructure tables SHOULD have explicit cleanup or retention
policies.

---

# 31. PostgreSQL Database Cache

When:

```text
CARE_CACHE_BACKEND=postgres
```

the configured cache table SHALL exist.

Operators SHALL monitor:

- table size;
- write volume;
- expired entries;
- cache query latency;
- impact on clinical queries.

The cache table contains disposable cache values.

Deleting all cache rows SHOULD not destroy durable CARE state.

---

# 32. Cache Table Maintenance

Database cache entries may remain until normal cache operations perform
cleanup.

For a large deployment, operators MAY add a maintenance command or scheduled
cleanup process if measurement shows unacceptable growth.

Any cleanup SHALL:

- target only the cache table;
- avoid long table locks;
- be tested in staging;
- preserve active application tables;
- produce observable logs.

The project SHALL not add complex cleanup before actual need is demonstrated.

---

# 33. PostgreSQL Rate-Limit State

If rate limiting uses explicit PostgreSQL models, operations SHALL define:

- retention window;
- cleanup cadence;
- indexes;
- concurrency semantics;
- failure policy.

Expired counter rows SHOULD be removed by a scheduled management command or
normal application operation.

Security-sensitive rate limits SHALL not silently fail open without an explicit
decision.

---

# 34. PostgreSQL Task Queue Operations

This section applies only if the optional PostgreSQL queue is accepted.

Operators SHALL monitor:

- queued jobs;
- oldest queued job;
- active jobs;
- failed jobs;
- retry count;
- worker heartbeat;
- worker connections;
- queue-table size;
- cleanup status.

An immediate PostgreSQL queue requires an active consumer.

If the worker is configured with minimum instances greater than zero, its
baseline cost SHALL be included in operational budgets.

---

# 35. PostgreSQL Queue Backlog

When backlog grows:

1. verify worker health;
2. inspect failed or locked tasks;
3. inspect database contention;
4. inspect queue concurrency;
5. inspect external dependency failures;
6. increase worker concurrency carefully;
7. increase active workers only within the database connection budget;
8. pause task producers if necessary.

Operators SHALL not delete queued clinical work without documented review.

---

# 36. Cloud Storage Buckets

The minimum logical storage areas are:

```text
patient
facility
report
```

They MAY use:

- separate physical buckets;
- or a documented shared bucket with separate prefixes.

Production buckets SHALL:

- block public access;
- use IAM-based access;
- use appropriate location;
- define retention or versioning decisions;
- define lifecycle rules only when safe;
- emit access logs or audit events where required.

---

# 37. Bucket Access

The frontend SHALL not access buckets directly.

The API and worker service accounts receive controlled access.

Operations SHALL verify:

- anonymous reads fail;
- anonymous writes fail;
- unrelated service accounts fail;
- authorized API and worker access succeeds;
- deletion permissions match application needs.

---

# 38. Bucket Lifecycle Rules

Lifecycle policies MAY clean:

- abandoned temporary objects;
- old object versions;
- development test prefixes;
- expired staging data.

Production lifecycle rules SHALL not delete active clinical objects based only
on object age unless CARE's data-retention policy explicitly requires it.

Lifecycle configuration SHALL be reviewed as a potential data-loss mechanism.

---

# 39. Bucket Versioning

Object versioning MAY be enabled where recovery value justifies the cost.

The decision SHALL consider:

- accidental deletion recovery;
- accidental overwrite recovery;
- storage cost;
- retention requirements;
- deletion semantics;
- privacy erasure requirements.

Enabling versioning does not replace database backups or application-level
authorization.

---

# 40. File Upload Operations

Uploads pass through the CARE API.

Operators SHALL monitor:

- request duration;
- request size;
- memory usage;
- temporary-disk usage;
- storage write failures;
- upload validation failures;
- incomplete upload records;
- API timeout rate.

The supported maximum upload size SHALL be documented.

Cloud Run memory and timeout configuration SHALL reflect measured upload
behavior.

---

# 41. File Download Operations

Downloads pass through CARE.

Operators SHALL monitor:

- streaming duration;
- first-byte latency;
- concurrent streams;
- storage read failures;
- memory use;
- API egress;
- request timeout rate.

Large download traffic MAY materially affect Cloud Run and network cost.

Any later move to a different download architecture SHALL require a separate
security and architecture decision.

---

# 42. Missing Storage Objects

A database record may occasionally reference a missing object because of:

- interrupted operation;
- administrative deletion;
- permission failure;
- software defect;
- manual bucket modification.

Operational handling SHALL include:

- controlled API response;
- structured error log;
- object identifier;
- database record identifier;
- no full clinical payload;
- investigation or cleanup procedure.

Operators SHALL not recreate missing clinical files with placeholder data.

---

# 43. Orphaned Storage Objects

An object may exist without a corresponding database record.

Potential causes include:

- database failure after upload;
- interrupted request;
- abandoned workflow;
- manual data changes.

A cleanup process MAY identify orphaned objects.

Automatic deletion SHALL not be implemented without a reliable way to prove
the object is unreferenced.

A quarantine or report-only mode SHOULD precede destructive cleanup.

---

# 44. Cloud Tasks Queue Operations

The default GCP task backend uses Cloud Tasks.

Operators SHALL monitor:

- dispatch failures;
- queue depth;
- oldest task age;
- retry count;
- worker response codes;
- worker latency;
- task execution duration;
- dead-letter or terminal failures if configured.

Each queue SHALL have documented:

- purpose;
- target worker;
- retry policy;
- rate limits;
- concurrency limits;
- execution deadline;
- owner.

---

# 45. Cloud Tasks Retry Policy

Retry policy SHALL reflect task semantics.

Email tasks may tolerate retries differently from report generation.

Operators SHALL know:

- maximum attempts;
- minimum backoff;
- maximum backoff;
- maximum retry duration;
- permanent failure behavior.

Increasing retries SHALL not substitute for fixing deterministic task errors.

---

# 46. Cloud Tasks Backlog

When the queue grows unexpectedly:

1. inspect worker health;
2. inspect Cloud Run errors;
3. inspect task response codes;
4. inspect database connectivity;
5. inspect storage and email dependencies;
6. inspect queue rate limits;
7. inspect worker maximum instances;
8. verify Cloud SQL connection headroom.

Raising worker scale limits SHALL be coordinated with the database connection
budget.

---

# 47. Failed Cloud Tasks

A failed task investigation SHOULD capture:

```text
task name
task identifier
attempt count
worker revision
failure category
related CARE record identifier
timestamp
```

It SHOULD NOT capture full sensitive payloads unless an approved diagnostic
process requires them.

Recovery MAY involve:

- correcting configuration;
- fixing application code;
- re-enqueueing a task;
- repairing application state;
- marking a task permanently failed.

Re-enqueueing SHALL respect idempotency requirements.

---

# 48. Private Worker Access

The worker SHALL remain private.

Operational verification SHALL periodically confirm:

- unauthenticated requests fail;
- only expected invokers have access;
- the public API does not expose the internal task route unintentionally;
- worker logs identify the invoker and task;
- IAM bindings have not broadened unexpectedly.

Application headers SHALL not replace Cloud Run IAM authentication.

---

# 49. Cloud Run Jobs

Jobs SHALL be used for:

```text
migrations
permission synchronization
value-set synchronization
cleanup
batch operations
administrative commands
```

Each job SHALL define:

- command;
- timeout;
- retries;
- service account;
- CPU and memory;
- environment variables;
- secret references;
- expected exit code;
- alerting.

---

# 50. Running a Job Manually

Operators MAY manually execute approved jobs for:

- deployment;
- maintenance;
- incident response;
- verification.

Before running a production job, verify:

- correct project;
- correct region;
- correct environment;
- correct image revision;
- correct command;
- expected impact;
- concurrency safety.

The operator SHOULD record the execution reason.

---

# 51. Migration Job Operations

Normal deployment sequence:

1. update migration job to the new image;
2. execute the job;
3. wait for completion;
4. inspect logs;
5. stop deployment if it fails;
6. deploy worker;
7. deploy API.

The API SHALL not deploy automatically after a failed migration.

A successful command exit is required.

---

# 52. Migration Failure

When a migration fails:

1. do not deploy the new API revision;
2. preserve logs;
3. determine whether the migration partially applied;
4. inspect Django migration state;
5. correct code or data in a controlled branch;
6. test on an isolated environment;
7. rerun only after review.

Operators SHALL not blindly fake migrations in production.

`--fake` usage requires an explicit understanding of schema state.

---

# 53. Scheduled Jobs

Cloud Scheduler SHALL trigger approved periodic work.

Expected schedules include:

```text
expired token-slot cleanup
incomplete file-upload cleanup
other documented maintenance commands
```

Each schedule SHALL define:

- timezone;
- cadence;
- authenticated target;
- retry behavior;
- disabled or enabled state;
- owner;
- alerting.

The configured timezone SHALL be explicit.

---

# 54. Scheduler Changes

When changing a production schedule:

1. document the old cadence;
2. document the new cadence;
3. assess overlap;
4. assess workload duration;
5. assess database load;
6. apply through Terraform;
7. verify the next execution;
8. verify no duplicate scheduler exists.

Celery Beat SHALL not schedule the same production job in the default GCP
profile.

---

# 55. API Deployment

The API deployment SHALL use an immutable image.

Before deployment:

- tests pass;
- image is published;
- migrations succeed;
- worker is deployed when required;
- configuration is validated;
- secrets exist;
- storage aliases resolve.

After deployment:

- health check passes;
- static file request passes;
- authenticated API smoke test passes;
- storage smoke test passes;
- task enqueue passes.

---

# 56. Worker Deployment

The worker SHOULD deploy before the API begins enqueueing tasks requiring the
new handler set.

Deployment order:

```text
migration job
worker
API
scheduler changes
```

The worker revision SHALL contain handlers required by the API revision.

This order reduces tasks arriving before their handler exists.

---

# 57. Cloud Run Revisions

Operators SHALL preserve revision traceability.

Each revision SHOULD identify:

```text
image digest
Git commit
upstream commit
deployment timestamp
environment
```

Traffic SHOULD normally move to the newly verified revision.

Canary or gradual traffic allocation MAY be used later if operationally useful.

---

# 58. Application Rollback

Application rollback uses a previous known-good Cloud Run revision or image.

Before rollback, verify:

- previous revision exists;
- secrets remain compatible;
- database schema remains compatible;
- task payloads remain compatible;
- worker and API revisions are compatible.

API and worker may need to roll back together.

Rollback SHALL not assume database migrations are reversible.

---

# 59. Worker and API Version Compatibility

During deployment, mixed revisions may coexist briefly.

Task payloads SHOULD therefore remain compatible across adjacent revisions
where practical.

Breaking task payload changes SHOULD use:

- versioned task names;
- versioned payload schemas;
- compatible transition logic;
- controlled deployment order.

The API SHALL not enqueue a payload unsupported by the active worker fleet.

---

# 60. Health Endpoints

The application SHOULD expose separate concepts for:

```text
liveness
readiness
diagnostics
```

Liveness answers:

```text
Is the process running?
```

Readiness answers:

```text
Can the process serve its configured role?
```

Diagnostics may report dependency state to authorized operators.

Sensitive infrastructure details SHALL not be publicly exposed.

---

# 61. API Readiness

API readiness SHOULD require:

- Django startup completed;
- required settings valid;
- PostgreSQL available.

It MAY require configured storage access if the application cannot operate
meaningfully without it.

It SHALL not require:

- Redis when Redis is disabled;
- Celery when Cloud Tasks is selected;
- worker availability through a synchronous request;
- every optional external integration.

---

# 62. Worker Readiness

Worker readiness SHOULD verify:

- application startup;
- handler registry;
- PostgreSQL;
- required storage configuration;
- required secrets.

Cloud Run IAM authorization is tested externally rather than through an
ordinary application health response.

---

# 63. Logging

All runtime processes SHALL log to stdout and stderr.

Logs SHOULD be structured.

Recommended fields:

```text
severity
timestamp
environment
service
revision
request_id
task_id
task_name
task_backend
attempt
duration_ms
status
```

Logs SHALL avoid:

- complete patient records;
- full request bodies;
- file contents;
- authentication tokens;
- signed credentials;
- passwords;
- secret values.

---

# 64. Log Retention

Log retention SHALL balance:

- incident investigation;
- audit needs;
- privacy;
- cost.

Development logs MAY use shorter retention.

Production logs MAY require longer retention according to policy.

Long retention SHALL not be used to justify logging sensitive payloads.

---

# 65. Log-Based Alerts

Useful alerts include:

```text
high API 5xx rate
worker task failures
migration job failure
scheduled job failure
Cloud SQL connection exhaustion
storage permission failures
repeated authentication failures
queue backlog
optional Redis failure
```

Alerts SHALL include enough context to identify the environment and revision.

They SHALL not include sensitive clinical content.

---

# 66. Metrics

Operators SHOULD monitor:

## API

```text
request count
latency
5xx rate
instance count
cold starts
memory
CPU
concurrency
```

## Worker

```text
task count
task duration
failure rate
retry rate
instance count
cold starts
```

## Cloud SQL

```text
connections
CPU
memory
storage
disk utilization
query latency
locks
```

## Storage

```text
operation errors
bytes stored
request count
egress
```

## Tasks

```text
queue depth
oldest task age
retry count
execution latency
```

---

# 67. Dashboards

At minimum, dashboards SHOULD provide:

```text
environment overview
API health
worker and task health
Cloud SQL health
storage failures
scheduled-job status
cost indicators
```

Operators SHOULD be able to identify:

- which revision is failing;
- whether failures are API, database, storage or task related;
- whether the issue affects one environment or all;
- whether an upstream synchronization introduced the failure.

---

# 68. Incident Severity

The project SHOULD define severity levels.

Example:

## Critical

```text
patient-data exposure
unauthorized access
database corruption
production unavailable
irrecoverable file loss
```

## High

```text
major API failure
task backlog affecting clinical work
database nearing exhaustion
storage access broadly failing
```

## Medium

```text
scheduled cleanup failure
optional cache failure
partial external integration outage
```

## Low

```text
development environment issue
noncritical dashboard problem
documentation defect
```

The exact policy SHALL be adapted to the operating organization.

---

# 69. Incident Response

A production incident SHOULD follow:

1. identify environment;
2. identify affected revision;
3. preserve relevant logs;
4. assess patient and data impact;
5. stop harmful operations if necessary;
6. roll back application code when safe;
7. disable problematic schedules or queues when necessary;
8. restore data only through approved procedures;
9. document actions;
10. perform post-incident review.

Operators SHALL avoid destructive ad hoc commands without preserving evidence.

---

# 70. Disabling a Scheduler Job

A failing scheduled job MAY be disabled temporarily.

The operator SHALL record:

- job name;
- reason;
- disable time;
- expected consequence;
- owner;
- restoration condition.

Disabling cleanup jobs may lead to:

- stale records;
- incomplete upload accumulation;
- increased storage use.

The operational consequence SHALL be understood.

---

# 71. Pausing Task Production

When the worker or a dependency is failing, the API MAY need to stop enqueueing
selected tasks.

This may be implemented through:

- configuration;
- feature flags;
- temporary endpoint restrictions;
- queue-specific controls.

The system SHALL not silently accept an asynchronous request and discard the
work.

The user-facing behavior SHALL be explicit.

---

# 72. Optional Redis Operations

This section applies only when Redis is enabled.

Operators SHALL know which responsibilities use Redis:

```text
cache
rate limiting
transient state
Celery
```

The application SHALL not treat Redis as one undifferentiated dependency.

---

# 73. Redis Connection Configuration

Redis connections SHOULD use:

```text
rediss://
```

when TLS is required.

Configuration SHALL define:

- timeout;
- connection pool behavior;
- retry policy;
- certificate verification;
- database or namespace strategy;
- maximum connections.

For serverless providers, connection limits and request pricing SHALL be
understood.

---

# 74. Upstash Operations

When Upstash is selected, operators SHOULD monitor:

- request volume;
- latency;
- plan limits;
- storage use;
- eviction;
- connection errors;
- regional location;
- TLS errors.

The application SHOULD remain provider-neutral.

Migrating away from Upstash SHOULD require configuration changes rather than
domain-code changes.

---

# 75. Redis Outage

Expected behavior depends on responsibility.

## Performance cache

May degrade to cache misses.

## Rate limiting

Must follow the documented security fallback.

## Progress state

May temporarily stop showing progress.

## Celery broker

Task dispatch fails until broker recovery.

The outage behavior SHALL be tested before production.

---

# 76. Email Operations

CARE email tasks use Django's email abstraction.

Operators SHALL monitor:

- send failures;
- authentication failures;
- rate limits;
- retry volume;
- rejected recipients;
- provider outages.

Email credentials SHALL remain in Secret Manager.

Task logs SHOULD avoid full message contents.

---

# 77. TOTP Notification Failures

Failure to send TOTP enabled or disabled notifications SHOULD be visible.

Operators SHALL distinguish:

- authentication configuration error;
- transient provider error;
- invalid recipient;
- application template error;
- worker failure.

Retries SHALL not generate uncontrolled duplicate email volume.

---

# 78. Cost Monitoring

Cost monitoring SHALL separate:

```text
Cloud SQL
Cloud Run
Cloud Storage
Cloud Tasks
Cloud Scheduler
Artifact Registry
Secret Manager
logging
network egress
optional Redis
```

Labels SHOULD permit environment and component attribution.

Development cost SHOULD not be confused with production cost.

---

# 79. Persistent Baseline Cost

The principal expected persistent baseline cost is Cloud SQL.

Other persistent costs include:

- stored data;
- retained backups;
- retained logs;
- retained images;
- optional managed Redis;
- a minimum-instance queue worker if selected.

The system SHALL not be described as entirely scale-to-zero.

---

# 80. Cost Controls

Useful cost controls include:

- Cloud Run maximum instances;
- minimum instances set to zero where appropriate;
- conservative Cloud SQL sizing;
- log retention limits;
- Artifact Registry cleanup;
- development environment shutdown or recreation;
- bucket lifecycle rules for synthetic data;
- task queue rate limits;
- alerting on unexpected spend.

Cost controls SHALL not delete production data automatically without policy.

---

# 81. Development Environment Teardown

A development environment MAY be destroyed and recreated when it contains only
synthetic data.

Before teardown, verify:

- no real patient data;
- no required test evidence;
- Terraform state is correct;
- no shared production resources;
- no shared buckets or secrets.

The teardown procedure SHALL target the correct environment explicitly.

---

# 82. Staging Environment

Staging SHOULD resemble production in:

- service topology;
- settings profile;
- IAM pattern;
- storage backend;
- task backend;
- migration process;
- health checks;
- deployment pipeline.

Staging MAY use smaller resources.

It SHALL not silently use local MinIO or Celery if production uses GCS and Cloud
Tasks, unless a particular test explicitly requires that profile.

---

# 83. Production Access

Production access SHOULD use:

- individual identities;
- multi-factor authentication;
- least privilege;
- audited role assignment;
- temporary elevation where practical.

Shared administrator accounts SHOULD be avoided.

Direct database access SHALL be limited.

Administrative changes SHALL be traceable to a person or deployment identity.

---

# 84. Manual Database Changes

Manual SQL in production SHOULD be avoided.

When required:

1. create a reviewed script;
2. test it in staging;
3. back up the database;
4. estimate lock and runtime impact;
5. execute with a named operator;
6. record results;
7. convert recurring changes into migrations or management commands.

Application data fixes SHALL not be hidden inside Terraform.

---

# 85. Manual Bucket Changes

Manual object deletion or movement SHOULD be avoided.

When required:

- verify the corresponding database record;
- verify authorization;
- preserve evidence;
- consider versioning;
- document the action;
- verify application behavior afterward.

Objects SHALL not be renamed manually unless database references are updated
consistently.

---

# 86. Key Rotation

Credential rotation procedures SHOULD exist for:

```text
database password
SMTP credentials
JWT or JWKS material
optional Redis credentials
external API credentials
```

Rotation steps SHOULD include:

1. create new credential;
2. add new secret version;
3. deploy or refresh dependent service;
4. verify operation;
5. revoke old credential;
6. verify no old revision still requires it;
7. document completion.

---

# 87. Django Secret Key Rotation

Rotating `DJANGO_SECRET_KEY` may invalidate:

- signed cookies;
- sessions;
- tokens or signatures depending on application use.

Rotation SHALL be planned.

If Django supports fallback signing keys in the deployed version, they MAY be
used during a controlled transition.

The exact procedure SHALL be validated against the CARE version.

---

# 88. Service Account Key Policy

Cloud Run runtime identities SHOULD use attached service accounts.

Static service-account key files SHOULD not be created for ordinary operation.

If an exceptional integration requires a key:

- justify it;
- restrict permissions;
- store it in Secret Manager;
- rotate it;
- monitor use;
- define removal plans.

---

# 89. Release Procedure

A production release SHOULD follow:

1. synchronize with upstream as planned;
2. merge approved feature work into `gcp`;
3. run CI;
4. build immutable image;
5. deploy to staging;
6. run staging smoke tests;
7. approve production plan;
8. run production migrations;
9. deploy worker;
10. deploy API;
11. update schedules;
12. run production smoke tests;
13. tag the release;
14. record upstream and image references.

---

# 90. Release Metadata

Each release SHOULD record:

```text
release tag
GCP commit SHA
upstream commit SHA
image digest
Terraform commit SHA
database migration state
deployment timestamp
operator or pipeline
```

This metadata MAY be stored in:

- release notes;
- deployment annotations;
- a release record;
- `UPSTREAM_BASE`;
- application version endpoint.

---

# 91. First Production Release

Because the deployment is greenfield, the first production release SHALL
verify:

- empty database initialization;
- first administrator workflow;
- first facility workflow;
- first user workflow;
- first patient workflow;
- first upload and download;
- first report;
- first task;
- first scheduled job;
- first backup;
- initial monitoring and alerting.

The environment SHALL not be considered ready merely because the API health
endpoint returns success.

---

# 92. Routine Maintenance

Routine operational work includes:

```text
upstream synchronization
dependency updates
security updates
database backup verification
restore testing
log-retention review
cost review
IAM review
secret rotation
task backlog review
scheduled-job review
storage-growth review
container cleanup
```

A maintenance calendar SHOULD assign cadence and ownership.

---

# 93. Suggested Maintenance Cadence

Example cadence:

## Daily

```text
critical alerts
failed jobs
task backlog
API availability
database capacity warnings
```

## Weekly

```text
error trends
scheduler success
storage failures
unexpected cost changes
```

## Monthly

```text
upstream changes
dependency updates
IAM review
Artifact Registry cleanup
cache and queue table growth
backup status
```

## Quarterly

```text
restore test
secret rotation review
disaster-recovery review
production access review
capacity review
```

The operating organization MAY adjust this cadence.

---

# 94. Dependency Updates

Dependency updates SHALL:

- use the repository's package manager;
- update lockfiles;
- run local tests;
- run storage tests;
- run task tests;
- build the production image;
- validate GCP settings;
- run staging smoke tests for significant updates.

Special attention SHALL be paid to:

```text
Django
django-storages
Google client libraries
Celery
Redis client
PostgreSQL queue library if enabled
Gunicorn
```

---

# 95. Security Updates

Security updates affecting deployed components SHALL be prioritized.

The process SHOULD:

1. identify exposure;
2. update the affected dependency or code;
3. run focused tests;
4. deploy to staging;
5. deploy an immutable production revision;
6. record the fix;
7. verify no vulnerable revision receives traffic.

The current image digest SHALL be known during incident response.

---

# 96. Disaster Recovery Scope

Disaster recovery SHALL address at least:

```text
Cloud SQL loss or corruption
bucket deletion or object loss
incorrect application deployment
secret compromise
service-account compromise
region-level service disruption
Terraform state loss
```

Not every scenario requires active multi-region deployment.

The expected recovery time and recovery point SHALL be documented according to
actual organizational needs.

---

# 97. Cloud SQL Recovery

Recovery options MAY include:

- point-in-time recovery;
- backup restore;
- restore to a new instance;
- application reconnection;
- DNS or configuration update;
- deployment of a compatible CARE revision.

Recovery SHALL be tested.

Operators SHALL not overwrite the failed source before investigation unless
urgently required.

---

# 98. Cloud Storage Recovery

Recovery depends on configured protections:

- versioning;
- retention;
- backups or exports;
- application metadata.

A database restore alone may not restore deleted objects.

A bucket recovery plan SHALL account for:

- object names;
- database references;
- versions;
- permissions;
- lifecycle policies.

---

# 99. Terraform State Recovery

Terraform state recovery SHALL use the remote backend's version history or
backup process.

Before applying with reconstructed state:

- verify resource identities;
- avoid accidental recreation;
- import existing resources when necessary;
- review the plan carefully;
- protect Cloud SQL and buckets.

Loss of state SHALL not trigger immediate destruction and recreation of
production.

---

# 100. Compromised Secret Response

When a secret is suspected compromised:

1. identify affected services;
2. create a replacement credential;
3. store a new secret version;
4. deploy dependent services;
5. revoke the old credential;
6. inspect access logs;
7. assess patient-data impact;
8. document the incident.

Rotating the secret without investigating use may be insufficient.

---

# 101. Compromised Service Account

Response SHOULD include:

1. disable or restrict the identity;
2. inspect IAM bindings;
3. inspect audit logs;
4. replace affected deployment identity;
5. rotate any associated keys;
6. redeploy services if necessary;
7. investigate accessed resources;
8. document scope and impact.

Runtime service accounts SHOULD not use static keys, reducing this risk.

---

# 102. Operational Runbook Format

Individual operational procedures SHOULD use a consistent template:

```markdown
# Procedure name

## Purpose

## Preconditions

## Environment

## Impact

## Commands or actions

## Verification

## Rollback

## Logging and evidence

## Owner
```

High-risk actions SHALL not exist only as informal chat instructions.

---

# 103. Required Runbooks

Before production use, create runbooks for:

```text
deploy CARE
roll back API and worker
run database migrations
restore Cloud SQL backup
rotate database password
rotate Django secret
disable a Scheduler job
re-enqueue a failed task
investigate task backlog
investigate missing object
investigate database connection exhaustion
recreate development environment
synchronize upstream
```

---

# 104. Operational Documentation Storage

Operational documentation SHALL be stored in the repository when it contains no
secrets.

Suggested layout:

```text
docs/gcp/runbooks/
├── deploy.md
├── rollback.md
├── migrate.md
├── restore-database.md
├── rotate-secrets.md
├── task-backlog.md
├── missing-file.md
├── scheduler.md
└── recreate-dev.md
```

Secret values and confidential incident details SHALL remain outside Git.

---

# 105. Production Readiness Checklist

Before first production use:

- [ ] Terraform state is remote and protected.
- [ ] Cloud SQL backups are enabled.
- [ ] Point-in-time recovery decision is documented.
- [ ] Cloud Storage buckets are private.
- [ ] Service accounts follow least privilege.
- [ ] No runtime service-account keys are used.
- [ ] Secrets are in Secret Manager.
- [ ] API runs on Cloud Run.
- [ ] Worker is private.
- [ ] Cloud Tasks invocation succeeds.
- [ ] Cloud Scheduler jobs are correct.
- [ ] Migration job succeeds.
- [ ] Storage upload and download pass through CARE.
- [ ] PostgreSQL cache works when selected.
- [ ] Redis is not required by the default profile.
- [ ] Logs exclude sensitive payloads.
- [ ] Alerts are configured.
- [ ] Restore procedure is documented.
- [ ] Application rollback is tested.
- [ ] Upstream base is recorded.
- [ ] Synthetic end-to-end tests pass.
- [ ] Initial administrator procedure is documented.

---

# 106. Routine Deployment Checklist

Before deployment:

- [ ] Correct environment selected.
- [ ] Worktree and branch verified.
- [ ] CI passed.
- [ ] Image digest recorded.
- [ ] Terraform plan reviewed.
- [ ] Migrations reviewed.
- [ ] Worker/API compatibility verified.
- [ ] Secrets exist.
- [ ] Backup status verified for high-risk migrations.

During deployment:

- [ ] Migration job succeeded.
- [ ] Worker deployed.
- [ ] API deployed.
- [ ] Scheduler changes applied.
- [ ] Smoke tests passed.

After deployment:

- [ ] Error rate normal.
- [ ] Task failures normal.
- [ ] Database connections normal.
- [ ] Storage operations normal.
- [ ] Release metadata recorded.

---

# 107. Operational Definition of Healthy

The production environment is healthy when:

- API readiness passes;
- authenticated CARE workflows succeed;
- database connections remain within budget;
- task queue age remains acceptable;
- worker failures remain within expected levels;
- scheduled jobs succeed;
- storage reads and writes succeed;
- backups complete;
- no critical security alerts exist;
- costs remain within expected range.

A green process-health indicator alone is not sufficient.

---

# 108. Operational Definition of Degraded

The environment is degraded when one or more non-total failures exist, such as:

```text
email provider unavailable
report generation delayed
optional Redis cache unavailable
scheduled cleanup failing
task retries elevated
storage latency elevated
```

The application MAY remain usable.

Operators SHALL communicate the affected capability and expected impact.

---

# 109. Operational Definition of Unavailable

The environment is unavailable when core CARE use cannot proceed, such as:

```text
API inaccessible
Cloud SQL unavailable
authentication broadly failing
authorization broadly failing
required storage inaccessible
critical data corruption
```

Unavailable status requires immediate incident handling.

---

# 110. Definition of Operational Readiness

CARE is operationally ready when:

- infrastructure can be created reproducibly;
- the application can be deployed from an immutable image;
- the database initializes from migrations;
- secrets are managed securely;
- API and worker roles are observable;
- files are stored and served through Django;
- tasks are visible and recoverable;
- scheduled jobs are visible;
- PostgreSQL cache is maintainable;
- optional Redis behavior is documented;
- backups and restore are tested;
- release and rollback procedures exist;
- cost and capacity are monitored;
- upstream synchronization is operationalized.

---

## 111. Next Document

The next document is:

```text
docs/gcp/07-configuration-reference.md
```

It will define:

- required environment variables;
- optional environment variables;
- backend-selection values;
- Cloud Run configuration;
- Cloud SQL configuration;
- Django Storage aliases;
- Cloud Tasks configuration;
- PostgreSQL cache configuration;
- optional PostgreSQL queue configuration;
- optional Redis configuration;
- validation rules;
- safe defaults;
- prohibited production defaults.
