# ADR-0006: Portable Runtime Profiles with GCP as the First Managed Target

- **Status:** Accepted
- **Date:** 2026-08-06
- **Decision Makers:** CARE Fork Maintainers
- **Supersedes:** None
- **Superseded by:** None

## Context

The project began with the practical goal of running CARE inexpensively on GCP without a permanently running VM.

During design, the broader requirement became explicit:

- CARE must remain usable locally;
- MinIO, Redis and Celery must remain supported for local or traditional deployments;
- application code should depend on Django and narrow internal contracts rather than a cloud provider;
- GCP is the first managed-cloud profile, not the only possible deployment.

The current local runtime uses continuously running Docker Compose services.

The initial GCP target should use managed or request-driven services where practical.

## Decision

CARE SHALL support explicit runtime profiles.

The initial profiles are:

### Local or traditional profile

```text
Django application
PostgreSQL
MinIO through Django Storage
Redis
Celery
Celery Beat
```

### Initial GCP profile

```text
Cloud Run API
Cloud SQL for PostgreSQL
Cloud Storage through Django Storage
Cloud Tasks
private Cloud Run task worker
Cloud Scheduler
Cloud Run Jobs
Secret Manager
Artifact Registry
Cloud Logging
optional Redis-compatible services
```

Application behavior SHALL remain provider-neutral.

Cloud-specific integrations SHALL be isolated in:

- deployment settings;
- backend implementations;
- startup commands;
- infrastructure code.

## Django and PostgreSQL

Django and Django ORM remain intentional architecture choices.

PostgreSQL remains CARE's durable system of record.

No repository abstraction over Django ORM is required.

## Runtime roles

The managed-cloud application image SHOULD support distinct roles:

```text
API
HTTP task worker
management or batch job
optional Celery worker
optional PostgreSQL queue worker
```

The same immutable image SHOULD be reused where practical.

Roles differ through commands, configuration, IAM and scaling.

## Initialization

Migrations and setup commands SHALL run explicitly through deployment jobs.

Normal API or worker instance startup SHALL not:

- run migrations;
- synchronize permissions;
- synchronize value sets;
- depend on Celery Beat.

## Scale to zero

The initial GCP profile SHOULD allow these components to scale to zero:

- API, when operational requirements permit;
- Cloud Tasks worker;
- Cloud Run Jobs when not executing.

Cloud SQL does not scale to zero and represents a baseline cost.

The architecture SHALL not claim the entire system is serverless or zero-cost when idle.

## Portability

Runtime-specific choices SHALL not leak into CARE domain logic.

GCP support SHALL not require:

- GCP credentials locally;
- GCS locally;
- Cloud Tasks locally;
- Cloud Run-specific branching in business code.

Future runtime profiles may be added through explicit implementation decisions.

## Redis

Redis SHALL remain optional in the GCP profile.

It may be enabled for selected responsibilities such as high-frequency cache or coordination after the appropriate ADRs and specifications are implemented.

## Security

The GCP profile SHALL use:

- private storage buckets;
- least-privilege service accounts;
- private worker invocation;
- Secret Manager;
- controlled Cloud SQL connectivity;
- no committed service-account keys;
- no direct frontend storage credentials.

## Consequences

### Positive

- Local and traditional operation remain supported.
- GCP can avoid permanent VMs and polling workers.
- Application logic remains portable.
- Cloud resources can use managed identities.
- Deployment roles become explicit.

### Negative

- Multiple supported profiles increase testing requirements.
- Configuration validation becomes more complex.
- Runtime capabilities differ between profiles.
- Cloud SQL remains a persistent cost.
- Operational documentation must distinguish profiles.

## Alternatives Considered

### Make GCP the only supported runtime

Rejected.

The application must remain locally usable and portable.

### Preserve the current Docker Compose topology in a VM

Rejected for the initial GCP profile.

It creates a continuously running VM and higher operational burden.

### Use Kubernetes as the universal runtime

Rejected.

It introduces unnecessary complexity for the initial requirements.

### Abstract every cloud service immediately

Rejected.

Only concrete supported profiles should be implemented.

## Out of Scope

This ADR does not define:

- detailed Terraform modules;
- CI/CD;
- exact Cloud Run sizing;
- exact Cloud SQL tier;
- AWS or Azure profiles;
- multi-region architecture.

## Related Documents

- ADR-0001 through ADR-0005
- IS-06: Runtime Profiles
- Operations guide
- Configuration reference

## Implementation Status

- [x] Decision accepted.
- [ ] Production container implemented.
- [ ] GCP settings implemented.
- [ ] Cloud SQL integrated.
- [ ] API deployed to Cloud Run.
- [ ] Private worker deployed.
- [ ] Jobs and Scheduler implemented.
- [ ] Redis-free GCP profile verified.
