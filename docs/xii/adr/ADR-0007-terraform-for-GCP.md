# ADR-0007: Terraform for GCP Infrastructure as Code

- **Status:** Accepted
- **Date:** 2026-08-06
- **Decision Makers:** CARE Fork Maintainers
- **Supersedes:** None
- **Superseded by:** None

## Context

The initial managed-cloud profile requires multiple coordinated GCP resources:

- APIs;
- IAM identities;
- Cloud Run services;
- Cloud Run Jobs;
- Cloud SQL;
- Cloud Storage;
- Cloud Tasks;
- Cloud Scheduler;
- Secret Manager;
- Artifact Registry;
- networking;
- monitoring.

Manual creation would make environments difficult to reproduce, audit, review and destroy safely.

The deployment is greenfield and can be created directly from declared infrastructure.

## Decision

Terraform SHALL be the infrastructure-as-code tool for the initial GCP profile.

Terraform SHALL manage the lifecycle and configuration of supported GCP infrastructure.

Application source code SHALL not create production infrastructure at runtime.

## Scope

Terraform SHALL manage, as applicable:

- required GCP APIs;
- Artifact Registry;
- service accounts;
- IAM bindings;
- Cloud SQL;
- databases or database users where appropriate;
- Cloud Storage buckets;
- Cloud Tasks queues;
- Cloud Scheduler jobs;
- Cloud Run API;
- Cloud Run worker;
- Cloud Run Jobs;
- Secret Manager resources and access bindings;
- required networking;
- monitoring and alerting foundations;
- environment-specific resource configuration.

## Application schemas

Terraform SHALL not contain embedded application SQL for creating:

- Django tables;
- database-cache tables;
- PostgreSQL queue schemas;
- application models.

Those SHALL be created through:

- Django migrations;
- Django management commands;
- approved queue-library schema tooling.

## Environments

Infrastructure SHALL support separate environment compositions for:

```text
dev
staging
prod
```

Environment separation SHALL include stateful resources and secrets.

Module reuse is encouraged, but modules SHALL not be introduced solely for aesthetic abstraction.

## State

Terraform state SHALL be remote and protected.

State storage SHALL:

- restrict access;
- support recovery or versioning;
- separate environments;
- be treated as sensitive infrastructure metadata.

## Plans and review

Production applies SHOULD use reviewed Terraform plans.

Plans SHALL be inspected for destructive changes, especially:

- Cloud SQL replacement;
- bucket deletion;
- secret deletion;
- IAM broadening;
- service-account replacement;
- queue deletion;
- networking changes.

## Resource protection

Stateful production resources SHOULD use appropriate protections, such as:

- deletion protection;
- lifecycle restrictions;
- bucket retention decisions;
- backup configuration.

Terraform destroy is not an application rollback mechanism.

## Secrets

Terraform may create secret resources and IAM bindings.

Secret values SHOULD be injected through a secure operational process and SHALL not be committed as plaintext Terraform variables.

Sensitive outputs SHALL be minimized.

## Consequences

### Positive

- Environments are reproducible.
- Infrastructure changes are reviewable.
- IAM and networking are versioned.
- Greenfield environments can be recreated.
- Drift becomes easier to detect.
- Deployment documentation can reference concrete code.

### Negative

- Terraform state must be protected.
- Provider and module versions require maintenance.
- Stateful-resource changes require careful planning.
- Some operational secret workflows remain outside Terraform.

## Alternatives Considered

### Manual GCP configuration

Rejected.

It is not reproducible or sufficiently auditable.

### Pulumi

Not selected.

Terraform has broad GCP support and matches the current project plan.

### Kubernetes manifests

Rejected.

Kubernetes is not the selected runtime.

### Application-created infrastructure

Rejected.

Infrastructure lifecycle must remain outside application execution.

## Out of Scope

This ADR does not define:

- the exact Terraform directory implementation;
- CI deployment permissions;
- an organization-wide GCP landing zone;
- multi-cloud infrastructure code;
- application database migrations.

## Related Documents

- ADR-0006: Portable Runtime Profiles
- IS-07: Infrastructure as Code
- GCP Operations Guide
- Configuration Reference

## Implementation Status

- [x] Decision accepted.
- [ ] Remote state configured.
- [ ] Environment layout implemented.
- [ ] GCP resources declared.
- [ ] IAM validated.
- [ ] Development environment applied.
- [ ] Destructive-change protections tested.
