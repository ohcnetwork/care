# ADR-0003: Configurable Asynchronous Execution

- **Status:** Accepted
- **Date:** 2026-08-06
- **Decision Makers:** CARE Fork Maintainers
- **Supersedes:** None
- **Superseded by:** None

## Context

CARE currently uses Celery with Redis for asynchronous execution and Celery Beat for periodic scheduling.

Repository inspection established that task decoration does not necessarily imply asynchronous execution:

- eight task definitions were identified;
- only a limited number of call sites dispatch tasks asynchronously;
- several task-decorated functions are called synchronously;
- some periodic work is registered through Celery Beat;
- migrations and initialization commands currently execute during Celery startup.

The project must preserve:

- local Docker Compose behavior;
- existing Celery compatibility;
- synchronous behavior where CARE currently invokes task logic synchronously;
- portability beyond a single cloud provider.

The initial GCP profile should avoid a permanently polling worker and use managed request-driven execution where appropriate.

However, Cloud Tasks is a deployment implementation, not the application architecture.

## Decision

CARE SHALL separate reusable task behavior from task-transport and worker frameworks.

The application SHALL support configurable asynchronous execution backends.

The initial supported execution profiles are:

```text
Local or traditional:
Celery + Redis

Initial GCP profile:
Cloud Tasks + private HTTP worker

Optional future profile:
A separately approved PostgreSQL-backed queue
```

Application call sites SHALL dispatch asynchronous work through a narrow application API.

The application SHALL not treat Celery as the definition of task behavior.

## Reusable task behavior

Task logic SHOULD be implemented as ordinary Python functions or services.

Framework-specific wrappers SHALL remain thin.

The conceptual structure is:

```text
Reusable operation
   ├── called synchronously where CARE requires synchronous behavior
   ├── called by a Celery task wrapper
   ├── called by a Cloud Tasks HTTP handler
   └── called by another approved backend wrapper
```

A function SHALL not become asynchronous merely because it is decorated as a Celery task today.

Existing call-site semantics SHALL be preserved unless an explicit implementation specification changes them.

## Dispatch contract

Asynchronous producers SHALL use a narrow dispatch contract conceptually equivalent to:

```python
enqueue_task(
    task_name,
    payload,
    delay_seconds=None,
    task_id=None,
)
```

The exact API SHALL remain limited to verified CARE requirements.

The initial contract SHALL NOT attempt to reproduce all Celery features.

Unless verified call sites require them, the abstraction SHALL not include:

- chains;
- chords;
- groups;
- canvases;
- arbitrary callbacks;
- arbitrary Python import paths;
- general workflow orchestration.

## Payloads

Task payloads SHALL be JSON-serializable.

Payloads SHOULD contain opaque identifiers rather than complete clinical records.

Task payloads SHALL NOT contain:

- Django model instances;
- querysets;
- open file handles;
- provider clients;
- credentials;
- unserializable objects;
- complete sensitive records when database identifiers are sufficient.

Task handlers SHALL reload required state from PostgreSQL.

## Transaction timing

When a task depends on a database change, dispatch SHOULD occur after successful commit using Django's transaction facilities, such as:

```python
transaction.on_commit(...)
```

A task SHALL not observe state that was subsequently rolled back.

## Celery profile

Celery SHALL remain supported for:

- local Docker Compose;
- upstream-compatible development;
- traditional deployments;
- installations that intentionally operate a Celery broker and worker.

Existing Celery task names and signatures SHOULD remain stable where practical.

Redis may remain Celery's broker and result backend in that profile.

## Cloud Tasks profile

Cloud Tasks SHALL be the initial managed asynchronous backend for GCP.

Cloud Tasks SHALL invoke a private CARE worker over authenticated HTTP.

The worker SHALL:

- require platform IAM authentication;
- accept only registered task names;
- reject arbitrary callables;
- validate payloads;
- execute reusable task behavior;
- return success only after successful execution;
- expose retriable failures correctly;
- avoid logging complete sensitive payloads;
- scale to zero when idle.

Google Cloud Tasks is an implementation of the asynchronous execution contract, not a dependency of CARE business logic.

## Other providers

This ADR does not require immediate implementations for AWS, Azure or other clouds.

Future backends MAY be added when there is a concrete deployment requirement.

New backends SHALL implement the same narrow behavior required by CARE rather than expanding the contract speculatively.

## Results

The asynchronous transport SHALL not be treated as the durable application result store.

Meaningful task results and status SHALL be persisted in:

- existing domain records;
- report records;
- explicit execution-state records;
- another appropriate PostgreSQL model.

Cloud Tasks HTTP response bodies SHALL not be used as a result backend.

Celery results MAY remain for compatibility where verified callers still rely on them, but such dependencies SHALL be inventoried and migrated deliberately.

## Retries

Every backend may retry work.

Retry policy SHALL distinguish:

- transient infrastructure or external-service failures;
- permanent validation or business failures.

Framework retry configuration and application exception classification SHALL be mapped explicitly.

Infinite or uncontrolled retries are prohibited.

## Idempotency

Task execution SHALL be treated as at-least-once.

Handlers SHALL tolerate duplicate delivery where required.

Idempotency SHOULD rely on:

- existing database state;
- unique constraints;
- conditional updates;
- explicit idempotency keys;
- execution records;
- object existence where appropriate.

Redis SHALL not be the sole correctness mechanism.

## Periodic work

Periodic scheduling is a distinct concern from request-triggered asynchronous dispatch.

For the GCP profile:

- Cloud Scheduler SHALL provide periodic triggers;
- Cloud Run Jobs SHOULD execute maintenance and batch commands;
- Cloud Tasks MAY be used for bounded scheduled work when appropriate.

For the local Celery profile:

- Celery Beat MAY remain supported.

The same production operation SHALL not be scheduled simultaneously by Celery Beat and Cloud Scheduler.

## Initialization and migrations

Database migrations, permission synchronization and value-set synchronization SHALL not depend on a permanently running Celery Beat process in the target runtime.

They SHALL execute through explicit deployment or job commands.

The API and task worker SHALL not run migrations automatically during normal instance startup.

## Consequences

### Positive

- CARE task behavior is no longer defined by Celery.
- Local Celery compatibility is preserved.
- GCP can use scale-to-zero task execution.
- Only truly asynchronous call sites need transport migration.
- Synchronous calls remain synchronous.
- Task behavior becomes easier to test.
- Future execution backends remain possible.

### Negative

- Thin wrappers must be maintained for multiple enabled backends.
- Retry semantics differ between implementations.
- Task results must move to explicit application state.
- Handlers require idempotency review.
- Periodic scheduling must be managed separately.
- Not every Celery feature is portable.

## Alternatives Considered

### Replace every Celery task with Cloud Tasks

Rejected.

Task decorators do not prove asynchronous intent, and several current calls execute inline.

### Retain Celery and use a managed Redis service in every deployment

Rejected as the only architecture.

It requires an active worker and makes Redis mandatory even where managed request-driven execution is preferable.

### Use Cloud Tasks directly throughout application code

Rejected.

It would couple CARE business code to GCP.

### Build a general workflow engine abstraction

Rejected.

CARE's verified requirements do not justify reproducing a workflow platform.

### Adopt a PostgreSQL queue as the default immediately

Rejected for the initial GCP profile.

A PostgreSQL queue requires an active consumer for prompt execution and must be evaluated separately.

## Out of Scope

This ADR does not choose:

- a PostgreSQL task-queue library;
- distributed-lock implementation;
- cache backend;
- Terraform layout;
- detailed Cloud Tasks queue policies;
- workflow orchestration;
- event sourcing;
- cross-cloud task implementations.

## Related Documents

- Task call-site inventory
- Cache and Redis inventory
- IS-03: Asynchronous Runtime Modernization
- ADR-0004: Configurable Application Cache
- ADR-0005: Distributed Locking
- ADR-0006: Portable Runtime Profiles

## Implementation Status

- [x] Decision accepted.
- [ ] Reusable task logic extracted.
- [ ] Narrow dispatcher implemented.
- [ ] Celery backend preserved.
- [ ] Cloud Tasks backend implemented.
- [ ] Private worker implemented.
- [ ] Periodic work moved to explicit scheduler and jobs.
- [ ] Initialization removed from Celery startup dependency.
