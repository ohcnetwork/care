```markdown
# ADR-0002: Server-Mediated File Transport

- **Status:** Accepted
- **Date:** 2026-08-06
- **Decision Makers:** CARE Fork Maintainers
- **Supersedes:** None
- **Superseded by:** None

---

## Context

CARE historically supported multiple file-transfer mechanisms.

The verified runtime included:

- direct browser-to-object-storage uploads through presigned URLs;
- direct downloads through provider-generated or provider-facing URLs;
- a Django-proxied upload endpoint that transmitted complete file contents as base64;
- provider-specific transport behavior coupled to S3/MinIO concepts.

ADR-0001 established Django Storage API as the single application-level abstraction for object persistence.

After completion of ES-01:

- ordinary object persistence uses Django Storage API;
- MinIO is supported locally through `S3Storage`;
- generic S3-compatible storage remains supported;
- GCS is supported through `GoogleCloudStorage`;
- signed upload URLs have been removed;
- signed download URLs have been removed;
- downloads are mediated by CARE;
- provider-specific bucket URLs are no longer part of the client contract.

The remaining transport issue is the upload representation.

The current Django-mediated upload path still transports complete file contents encoded as base64.

Base64 file transport has several disadvantages:

- approximately 33% representation overhead before additional JSON overhead;
- complete file contents tend to be materialized in memory;
- normal browser and HTTP file-upload facilities are bypassed;
- Django upload handlers cannot be used naturally;
- large-file handling becomes less efficient;
- API schemas represent binary content as application JSON instead of file content.

The application should expose one provider-independent HTTP file contract regardless of which object-storage backend is configured.

---

## Decision

All supported file uploads and downloads SHALL be mediated by CARE.

Clients SHALL communicate only with CARE.

CARE SHALL communicate with object storage exclusively through Django Storage API as established by ADR-0001.

The target upload flow is:

```text
Client
  |
  | multipart/form-data
  v
CARE Django API
  |
  | UploadedFile / Django upload handlers
  v
CARE validation and authorization
  |
  v
Django Storage API
  |
  v
Configured object-storage backend
```

The target download flow is:

```text
Client
  |
  | authenticated CARE request
  v
CARE Django API
  |
  | authorization
  v
Django Storage API
  |
  | file-like object
  v
streaming HTTP response
```

The public HTTP contract SHALL be independent of:

- MinIO;
- AWS S3;
- S3-compatible providers;
- Google Cloud Storage;
- future Django-compatible storage providers.

---

## Upload Transport

File uploads SHALL use:

```text
multipart/form-data
```

CARE SHALL receive uploaded content through Django's normal upload facilities.

The implementation SHOULD use:

- `UploadedFile`;
- `InMemoryUploadedFile`;
- `TemporaryUploadedFile`;
- Django upload handlers;
- DRF file fields where applicable.

CARE SHALL NOT require complete file contents to be embedded inside JSON.

The existing base64 file-content transport SHALL be removed from the target API.

---

## Download Transport

Downloads SHALL continue to pass through authenticated CARE endpoints.

CARE SHALL:

1. authenticate the caller;
2. authorize access;
3. resolve the logical storage alias;
4. open the object through Django Storage;
5. return the object using a streaming response such as `FileResponse`;
6. set appropriate content type;
7. set safe content disposition;
8. handle missing objects consistently.

The storage provider SHALL not define the public download contract.

---

## Direct Object-Storage Access

Clients SHALL NOT:

- request presigned upload URLs;
- request presigned download URLs;
- upload directly to MinIO;
- upload directly to AWS S3;
- upload directly to GCS;
- download directly from provider-generated storage URLs as the normal application flow;
- receive storage credentials;
- select storage buckets;
- depend on storage-provider endpoints.

Provider-specific URLs SHALL NOT be part of the normal CARE API contract.

---

## Provider Portability

The same upload and download API SHALL work with any configured Django Storage backend supported by CARE.

Changing:

```text
CARE_STORAGE_BACKEND=s3
```

to:

```text
CARE_STORAGE_BACKEND=gcs
```

or another future supported backend SHALL NOT require frontend changes.

Provider selection remains a server-side deployment concern.

---

## Authorization

CARE SHALL remain the authorization boundary for file access.

Knowledge of:

- an object name;
- a bucket name;
- a previous download path;

SHALL NOT constitute authorization.

Uploads and downloads SHALL continue using CARE's existing permission and domain model.

This ADR does not redesign authorization.

---

## Validation

Uploads SHALL pass through CARE validation.

The implementation SHALL preserve or enforce applicable rules for:

- file presence;
- maximum file size;
- file extension;
- MIME type;
- logical file type;
- associated patient or facility;
- ownership;
- authorization;
- filename safety.

Browser-provided MIME metadata SHALL not automatically be treated as authoritative when stronger existing validation exists.

This ADR does not require adding heavyweight content-inspection or antivirus infrastructure.

---

## Upload Memory Management

The implementation SHALL use Django upload-handler behavior rather than base64-decoding complete request bodies.

Small files MAY remain in memory.

Larger supported files SHOULD be represented by temporary-file-backed uploads according to Django configuration.

Relevant limits SHALL be explicit.

Examples include:

```text
CARE_MAX_UPLOAD_SIZE
FILE_UPLOAD_MAX_MEMORY_SIZE
DATA_UPLOAD_MAX_MEMORY_SIZE
```

Exact setting names SHALL follow the project's configuration reference.

Temporary files are ephemeral and SHALL NOT be treated as durable storage.

---

## Persistence

After HTTP validation, file persistence SHALL continue through Django Storage API.

Where possible, the `UploadedFile` or equivalent file-like object SHOULD be passed directly to:

```python
storage.save(name, uploaded_file)
```

The transport layer SHOULD NOT perform an unnecessary complete `.read()` followed by a second in-memory representation.

Object naming and logical storage-alias selection remain governed by ADR-0001 / ES-01.

---

## Database and Storage Consistency

PostgreSQL and object storage do not participate in a shared atomic transaction.

The implementation SHALL therefore define failure behavior for cases such as:

- storage write fails;
- database update fails after storage write;
- object exists but metadata creation fails;
- incomplete upload state remains.

The implementation SHALL use the smallest correct compensation or cleanup strategy.

This ADR does not introduce distributed transactions.

---

## Response Contract

Successful upload responses SHALL remain provider-neutral.

They MAY expose application-level values such as:

- CARE file identifier;
- filename;
- MIME type;
- size;
- metadata;
- CARE-relative `download_url`;
- logical processing status.

They SHALL NOT expose:

- bucket URL;
- storage endpoint;
- S3 URL;
- GCS URL;
- signed URL;
- storage credentials.

---

## Streaming Downloads

Normal downloads SHOULD be streamed.

The application SHALL NOT read complete objects into memory merely to construct ordinary file responses.

Whole-file reads may remain inside internal processing operations that explicitly require complete bytes.

Those internal processing cases are not considered HTTP file transport.

---

## HTTP Range Requests

HTTP range support is not guaranteed by this decision.

If media seeking or large-file requirements later require byte ranges, that capability SHALL be designed and tested explicitly.

Range support SHALL not be assumed merely because the underlying object-storage provider supports it.

---

## Static Files

This ADR does not apply to Django static assets.

Static files continue using the existing Django/WhiteNoise configuration established by the project.

---

## Consequences

### Positive

- The client is completely independent of the storage provider.
- CARE remains the single authentication and authorization boundary.
- Base64 overhead is removed.
- Django upload handlers become usable.
- Large supported uploads can avoid unnecessary in-memory duplication.
- MinIO, S3 and GCS share the same HTTP contract.
- Provider changes do not require frontend changes.
- Storage credentials remain server-side.
- Validation and audit behavior remain centralized.

### Negative

- All file traffic passes through the CARE application runtime.
- Application bandwidth usage increases compared with direct-to-bucket transfers.
- File-transfer duration contributes to request execution time.
- Large-file support requires explicit runtime sizing and limits.
- Extremely large uploads may eventually require a different transport design.

---

## Alternatives Considered

### Preserve Base64 Uploads

Rejected.

Base64 is inefficient for general binary HTTP transport and prevents natural use of Django upload handlers.

### Reintroduce Presigned Uploads

Rejected.

Presigned uploads expose storage-provider behavior to clients and break the selected provider-neutral application boundary.

### Use Presigned Uploads Only for GCS or S3

Rejected.

The client contract must not depend on the configured provider.

### Use Presigned Uploads Only for Large Files

Deferred.

A future ADR may introduce a specialized large-object transport if actual requirements demonstrate that the server-mediated model is insufficient.

### Build a Custom Streaming Upload Framework

Rejected.

Django already provides established multipart and upload-handler abstractions.

### Use Provider-Native Multipart or Resumable Uploads

Deferred.

These mechanisms increase provider coupling and are unnecessary for the initial verified requirements.

---

## Out of Scope

This ADR does not define:

- object-storage provider selection;
- storage backend implementation;
- Cloud Tasks;
- Celery migration;
- report-generation retry behavior;
- Redis;
- cache;
- distributed locks;
- rate limiting;
- Cloud Run deployment;
- Cloud SQL;
- Terraform;
- CI/CD;
- CDN architecture;
- antivirus scanning;
- resumable provider-native uploads;
- very large video ingestion.

These concerns are governed by separate ADRs and Engineering Specifications.

---

## Relationship to ADR-0001

ADR-0001 answers:

> How does CARE persist and retrieve objects independently of the storage provider?

Answer:

```text
Django Storage API
```

ADR-0002 answers:

> How do file bytes travel between clients and CARE?

Answer:

```text
multipart upload through CARE
streaming download through CARE
```

The two concerns are intentionally separate.

---

## Related Documents

- ADR-0001: Portable Object Storage using Django Storage API
- ES-01: Portable Storage Modernization
- ES-02: File Transport Modernization
- Frontend File Flow Inventory
- Storage Call-Site Inventory
- Configuration Reference
- Testing Strategy

---

## Implementation Status

Current state after ES-01:

- [x] Provider-specific signed uploads removed.
- [x] Provider-specific signed downloads removed.
- [x] Downloads mediated by CARE.
- [x] Download persistence uses Django Storage.
- [x] Provider URLs removed from the normal client contract.
- [ ] Base64 upload transport removed.
- [ ] Multipart upload implemented.
- [ ] Django upload handlers verified.
- [ ] Upload size limits verified/configured.
- [ ] Multipart API schema implemented.
- [ ] Upload authorization regression tests completed.
- [ ] MinIO multipart round trip verified.
- [ ] Provider-neutral GCS multipart behavior verified.
- [ ] ES-02 completed.
```
