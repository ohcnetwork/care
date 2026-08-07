# ADR-0001: Portable Object Storage using Django Storage API

- **Status:** Accepted
- **Date:** 2026-08-06
- **Decision Makers:** CARE GCP Fork Maintainers
- **Supersedes:** None
- **Superseded by:** None

---

# Context

CARE currently implements object persistence through provider-specific code built
around MinIO and Amazon S3 semantics.

The current implementation directly depends on provider SDKs (primarily `boto3`)
through custom storage management classes and helper functions.

This approach has several disadvantages:

- the application is coupled to one provider implementation;
- object persistence logic is mixed with provider-specific behavior;
- switching storage providers requires application changes;
- introducing new providers requires additional storage implementations;
- testing requires mocking provider SDKs instead of using Django abstractions;
- ordinary CRUD operations bypass Django's storage interface.

The project intends to support several deployment profiles:

- local development;
- self-hosted deployments;
- generic S3-compatible object storage;
- Google Cloud Platform;
- future cloud providers where appropriate.

The application itself should not require modifications when changing object
storage providers.

---

# Decision

CARE SHALL adopt Django's Storage API as the single application-level abstraction
for object persistence.

Provider-specific SDKs SHALL NOT be used directly by application code for normal
object persistence operations.

Provider implementations SHALL be delegated to `django-storages`.

The resulting architecture is:

CARE

↓

Django Storage API

↓

django-storages

↓

Provider backend

Where the provider backend may be:

- S3Storage
- GoogleCloudStorage
- another Django-compatible backend in the future

---

# Local profile

The default local development profile SHALL continue using MinIO.

MinIO SHALL be accessed through:

```text
storages.backends.s3.S3Storage
```

The local Docker environment SHALL continue working without:

- Google Cloud credentials;
- service-account JSON files;
- GCP projects;
- internet connectivity to GCP.

The default backend SHALL therefore remain S3-compatible.

---

# Cloud profile

Google Cloud Storage SHALL be supported as the initial managed-cloud deployment
profile.

Google Cloud Storage is **not** the architecture.

Google Cloud Storage is one implementation of the storage abstraction.

Switching between MinIO and Google Cloud Storage SHALL require configuration
changes only.

Application code SHALL remain unchanged.

---

# Logical storage aliases

Application code SHALL refer only to logical storage aliases.

Initial aliases are:

- patient
- facility
- report
- staticfiles

Application code SHALL NOT know which provider implements an alias.

Aliases represent business intent rather than infrastructure.

---

# Configuration

Storage provider selection SHALL be configuration-driven.

A setting similar to:

```text
CARE_STORAGE_BACKEND
```

SHALL determine which provider implementation is used.

Initial supported values are expected to include:

- s3
- gcs

The default SHALL remain:

```text
s3
```

No provider-specific branching SHALL exist in application logic.

Provider selection belongs entirely in Django settings.

---

# Object persistence

Ordinary persistence operations SHALL use Django Storage methods such as:

- save
- open
- exists
- delete
- size

Application code SHALL NOT instantiate:

- boto3 clients
- Google Cloud Storage clients
- provider-specific CRUD helpers

for ordinary persistence.

---

# File transport

This ADR is about object persistence. It does not define the HTTP transport
layer, which is ADR-0002's subject.

**Revised 2026-08-07.** As originally written this section said the upload and
download APIs would remain unchanged until a later transport phase. That did not
survive contact with the decision itself: presigned URLs are provider-specific
by construction, so leaving them in place would have left a provider seam in the
one place this ADR set out to remove it, and would have kept every bucket
public. The IS-01 completion pass therefore removed them.

Removed by IS-01:

- browser presigned uploads;
- browser presigned downloads;
- the unsigned bucket URLs serving cover images and avatars.

Objects are now read back through CARE, which authorizes each request and
streams the bytes through Django Storage. Every bucket can be private.

Still outstanding, and genuinely out of scope here:

- **base64 uploads.** `POST /api/v1/files/upload-file/` still accepts a base64
  body and still buffers the decoded file in memory. Replacing it with
  `multipart/form-data` is a transport-performance change that does not affect
  provider portability, so it belongs to IS-02 under ADR-0002.

---

# Static files

Static assets SHALL continue using Django's existing staticfiles backend.

This ADR applies only to application object storage.

---

# Compatibility

The implementation SHOULD preserve compatibility with:

- MinIO
- AWS S3
- S3-compatible providers supported by django-storages
- Google Cloud Storage

No implementation shall assume a specific provider unless required by provider
configuration.

---

# Consequences

## Positive

- Provider portability.
- Simpler testing.
- Better alignment with Django architecture.
- Smaller maintenance surface.
- Easier future provider additions.
- Cleaner separation between application and infrastructure.
- Reduced provider-specific code.

## Negative

- Some provider-specific optimizations may require redesign.
- Existing storage helpers require refactoring.
- Temporary compatibility code may be required during migration.

---

# Alternatives Considered

## Keep the existing boto3-based implementation

Rejected.

It increases provider coupling and duplicates functionality already provided by
Django.

---

## Create a custom storage abstraction

Rejected.

Django already defines a mature storage abstraction.

Introducing another abstraction would duplicate framework functionality and
increase maintenance cost.

---

## Implement separate managers for each provider

Examples:

- S3FilesManager
- GCSFilesManager
- AzureFilesManager

Rejected.

This approach scales poorly and encourages provider-specific application logic.

---

## Adopt Google Cloud Storage directly

Rejected.

The objective is provider portability.

Google Cloud Storage is an implementation target, not the architectural
abstraction.

---

# Out of Scope

This ADR does not define:

- multipart uploads;
- frontend upload APIs;
- signed URL removal;
- Cloud Tasks;
- Celery replacement;
- Redis replacement;
- PostgreSQL cache;
- Terraform;
- deployment automation.

These subjects are addressed by separate ADRs and implementation
specifications.

---

# Related Documents

- Architecture 00–07
- Runtime Inventory
- Storage Inventory
- IS-01 Storage Modernization
- ADR-0002: Server-Mediated File Transport
- ADR-0003: Configurable Asynchronous Execution
- Future ADR: Cache and Distributed Locks

---

# Implementation Status

- [x] Decision accepted.
- [x] IS-01 completed. *(2026-08-07)*
- [ ] IS-02 completed.
- [x] Legacy storage removed. *`S3FilesManager` survives only as a deprecated
  plugin shim delegating to Django Storage; `care/utils/csp/` is deleted.*
- [x] Legacy signed URL flows removed. *No application code generates a
  storage-provider URL. Objects are served by CARE through Django Storage.*

## What IS-01 delivered

- Django Storage API is the single object-persistence abstraction; provider
  implementations come from `django-storages`.
- `CARE_STORAGE_BACKEND` selects `s3` (default) or `gcs`. Switching is a
  configuration change only — no application code path differs.
- Logical aliases `patient`, `facility` and `report`; `staticfiles` unchanged on
  WhiteNoise.
- All object transport is mediated by CARE. Presigned upload and download are
  gone, along with the unsigned bucket URLs that served cover images and
  avatars. Every bucket can now be private.

## Remaining for IS-02

The base64 upload transport at `POST /api/v1/files/upload-file/` is retained and
still buffers the decoded file in memory. IS-02 replaces it with
`multipart/form-data` and Django upload handlers. That is transport
performance, not provider portability, and does not affect this decision.
