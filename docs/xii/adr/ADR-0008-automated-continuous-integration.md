# ADR-0008: Automated Continuous Integration and Controlled Delivery

- **Status:** Accepted
- **Date:** 2026-08-06
- **Decision Makers:** CARE Fork Maintainers
- **Supersedes:** None
- **Superseded by:** None

## Context

The maintained CARE fork must:

- preserve the upstream-compatible local runtime;
- test multiple runtime profiles;
- produce immutable container images;
- deploy explicit database migrations;
- deploy worker and API revisions in a compatible order;
- validate Terraform;
- record the upstream base;
- support controlled rollback.

Manual build and deployment would make releases inconsistent and difficult to audit.

The repository is hosted on GitHub and can use GitHub Actions unless a later operational constraint requires another CI system.

## Decision

The project SHALL implement automated continuous integration and controlled delivery.

GitHub Actions SHALL be the initial CI/CD platform.

CI SHALL validate every relevant change.

Production delivery SHALL remain gated and auditable.

## Continuous integration

CI SHALL include appropriate stages for:

- formatting;
- linting;
- upstream CARE tests;
- GCP or portable-settings tests;
- storage tests;
- file-transport tests;
- task tests;
- cache and lock tests as implemented;
- container build;
- Terraform formatting and validation;
- security or secret scanning where practical.

Not every live-cloud integration test must run on untrusted pull requests.

Credentialed tests may run on:

- protected branches;
- approved workflows;
- staging deployment;
- scheduled tests.

## Immutable images

The pipeline SHALL build an immutable container image.

Images SHALL be identified using:

- Git commit SHA;
- release tag;
- image digest.

The API, task worker and jobs SHOULD use the same image revision.

## Deployment order

The controlled deployment sequence SHALL be:

1. validate code and infrastructure;
2. build and publish the image;
3. update the migration job;
4. run migrations;
5. stop on migration failure;
6. deploy the task worker;
7. deploy the API;
8. update jobs and schedules;
9. run smoke tests;
10. record release metadata.

The worker SHALL normally deploy before an API revision that produces new task payloads.

## Migrations

Migrations SHALL be explicit deployment operations.

API or worker startup SHALL not be the migration mechanism.

The pipeline SHALL not deploy the new API when migrations fail.

Destructive migrations SHOULD use expand-and-contract techniques where practical after real production data exists.

## Environment promotion

Changes SHOULD be verified in staging before production.

Production deployment SHOULD require an approved workflow or environment gate.

The exact approval model may depend on the operating organization.

## Secrets and identity

CI/CD SHALL use protected deployment identity.

Long-lived static service-account keys SHOULD be avoided.

Workload identity federation or another short-lived identity mechanism SHOULD be preferred where supported.

Secrets SHALL not be printed in logs.

## Rollback

Application rollback SHALL deploy a previous immutable revision.

The pipeline SHALL record enough metadata to identify:

- application commit;
- upstream commit;
- image digest;
- Terraform commit;
- migration state.

Database rollback is separate and SHALL not happen automatically.

## Upstream synchronization

CI SHALL validate synchronization branches against:

- the local upstream-compatible profile;
- the selected managed-cloud profile;
- container build;
- Terraform validation.

The release metadata SHALL record the upstream base commit.

## Consequences

### Positive

- Releases become repeatable.
- Tests gate changes.
- Images are traceable.
- Migration failures stop deployment.
- Worker/API compatibility can be controlled.
- Rollback references are preserved.
- Upstream synchronization is safer.

### Negative

- CI workflows require maintenance.
- Live integration tests require secure credentials.
- Multiple profiles increase build time.
- Database migrations still require human judgment.
- Pipeline permissions are security-sensitive.

## Alternatives Considered

### Manual deployment

Rejected.

It is error-prone and difficult to audit.

### Automatically deploy every branch to production

Rejected.

Production requires controlled promotion.

### Run migrations during container startup

Rejected.

Multiple concurrent instances and failed startup can create unsafe deployment behavior.

### Build separate images for every role

Rejected as the default.

A shared immutable image reduces drift unless role-specific needs later justify separation.

## Out of Scope

This ADR does not define:

- the exact YAML workflows;
- organization-wide release governance;
- a particular branching service beyond the documented fork strategy;
- automated database rollback;
- multi-cloud delivery pipelines.

## Related Documents

- ADR-0006: Portable Runtime Profiles
- ADR-0007: Terraform for GCP Infrastructure as Code
- IS-08: Continuous Delivery
- Testing Strategy
- Upstream Synchronization
- Operations Guide

## Implementation Status

- [x] Decision accepted.
- [ ] CI checks implemented.
- [ ] Immutable image build implemented.
- [ ] Terraform validation implemented.
- [ ] Staging deployment implemented.
- [ ] Migration gate implemented.
- [ ] Worker/API deployment order implemented.
- [ ] Production approval implemented.
- [ ] Release metadata recorded.
