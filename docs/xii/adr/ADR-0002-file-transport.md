# ADR-0002: Server-Mediated File Transport

- **Status:** Accepted
- **Date:** 2026-08-06
- **Decision Makers:** CARE Fork Maintainers
- **Supersedes:** None
- **Superseded by:** None

## Context

CARE currently supports more than one file-transfer flow.

The verified runtime includes:

- direct browser-to-object-storage uploads using presigned URLs;
- direct downloads using provider-generated URLs;
- an upload endpoint that sends file content through Django encoded as base64;
- custom S3-compatible persistence implemented with `boto3`.

ADR-0001 defines Django Storage API as the application-level object-persistence abstraction. It does not define how file bytes travel between clients and CARE.

The existing transport mechanisms create several problems:

- the frontend must understand provider-specific upload workflows;
- browser clients communicate directly with MinIO or another object-storage provider;
- bucket endpoints and signed URLs become part of the public application contract;
- authorization is divided between CARE and temporary provider credentials;
- base64 increases request size and memory use;
- complete files may be materialized in memory;
- provider changes can affect frontend behavior;
- direct uploads make validation and audit behavior more difficult to centralize;
- local and cloud deployments may expose different file-transfer behavior.

The initial deployment is greenfield. There is no production frontend or existing file population that requires preservation of the current transport contract.

## Decision

All supported file uploads and downloads SHALL pass through CARE Django endpoints, authenticated except for the two public asset classes named under [Authorization](#public-asset-exception).

The frontend SHALL communicate only with CARE.

CARE SHALL communicate with object storage through Django Storage API as established by ADR-0001.

The target upload flow is:

```text
Client
  |
  | multipart/form-data
  v
CARE Django API
  |
  | Django UploadedFile / upload handlers
  v
Django Storage API
  |
  v
Configured storage backend
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

## Upload transport

Uploads SHALL use:

```text
multipart/form-data
```

CARE SHALL use Django upload handlers and `UploadedFile` objects.

CARE SHALL avoid loading complete supported files into memory when temporary-file or streaming behavior is available.

The base64 upload contract SHALL be removed from the target production API.

## Download transport

Downloads SHALL be returned by CARE using a streaming response such as Django's `FileResponse` or an equivalent implementation.

CARE SHALL determine:

- authorization;
- content type;
- content disposition;
- safe filename;
- missing-object behavior.

The storage provider SHALL not define the public application response.

## Direct object-storage access

The frontend SHALL NOT:

- request presigned upload URLs;
- upload directly to MinIO;
- upload directly to S3;
- upload directly to GCS;
- receive storage credentials;
- select a bucket;
- depend on a storage-provider endpoint;
- use provider-generated download URLs as the normal download flow.

Presigned upload and download endpoints SHALL be removed from the target API.

## Provider portability

The HTTP file contract SHALL remain identical regardless of whether the configured storage backend is:

- MinIO;
- AWS S3;
- another S3-compatible provider;
- Google Cloud Storage;
- another future Django-compatible storage backend.

Changing the storage provider SHALL not require frontend changes.

## Authorization

CARE SHALL authenticate and authorize every upload and download.

Object-storage possession or knowledge of an object name SHALL not constitute application authorization.

### Public asset exception

Two asset classes are deliberately exempt from *authentication*, and only those
two: **facility cover images** and **user profile pictures**, served by
`facility-cover-image-asset` and `user-profile-picture-asset`
(`care/emr/api/viewsets/file_assets.py`).

These objects were already world-readable directly from the bucket before
ADR-0001. Requiring authentication to read them would be a new restriction
rather than a preserved one, and the routes exist to make the *bucket* private,
not to make the images less visible. Who can see them is unchanged; what changed
is that CARE serves the bytes, so no provider URL is exposed and no object needs
a public ACL.

Uploading or replacing either asset remains authenticated and authorized.

Every other download — clinical files and generated reports — SHALL require an
authenticated, authorized CARE request. No further exemption SHALL be added
without amending this ADR.

Authorization SHALL continue to follow CARE's existing domain and permission model.

This ADR does not redesign CARE permissions.

## Validation

Uploads SHALL pass through CARE validation.

The implementation SHALL enforce the applicable existing policies for:

- file size;
- filename;
- file extension;
- MIME type;
- ownership;
- patient or facility association;
- allowed operation.

The browser-supplied MIME type SHALL not automatically be treated as authoritative.

## Memory and temporary files

CARE SHALL configure explicit request and upload limits.

The implementation SHALL use Django's upload-handler behavior to move sufficiently large uploads to temporary files.

Temporary filesystem storage is ephemeral and SHALL not be considered durable.

Supported maximum file size SHALL be measured and documented.

Very large media-transfer workflows are outside the initial scope.

## Streaming

Downloads SHALL be streamed where possible.

The implementation SHALL not call `.read()` on an entire storage object merely to build a normal HTTP response.

Whole-file reads may remain in internal operations that explicitly require complete bytes, such as a rendering library, but they SHALL not be the default transport pattern.

## HTTP range requests

Range-request support is not guaranteed by this decision.

If video or audio seeking requires ranges, that capability SHALL be implemented and tested explicitly.

The initial transport implementation MAY document range requests as unsupported.

## Consequences

### Positive

- The frontend becomes storage-provider independent.
- CARE remains the single authorization boundary.
- File validation is centralized.
- Storage credentials and bucket endpoints remain server-side.
- Base64 overhead is removed.
- MinIO and GCS use the same application API.
- File operations are easier to audit.
- Provider changes do not alter the client contract.

### Negative

- File bytes pass through CARE and Cloud Run or the selected application runtime.
- API bandwidth, request duration and resource use increase.
- Large files require careful upload-handler and timeout configuration.
- Direct provider acceleration is not used.
- Cloud Run request limits constrain supported file sizes and durations.

## Alternatives Considered

### Preserve presigned browser uploads

Rejected.

It exposes storage-provider behavior to clients and conflicts with the selected provider-neutral CARE API boundary.

### Preserve base64 uploads

Rejected.

Base64 increases payload size, increases memory pressure and is not an appropriate general file-transfer mechanism.

### Use presigned uploads only for large files

Deferred.

The initial scope prioritizes a single simple transport contract. A separate ADR may reconsider exceptionally large-object workflows after real requirements and measurements exist.

### Stream uploads directly from the request to storage without Django upload handlers

Rejected as a general requirement.

The implementation should use Django's established request and upload abstractions unless measurements prove they are insufficient.

## Out of Scope

This ADR does not define:

- the configured object-storage provider;
- Cloud Tasks;
- cache backends;
- distributed locks;
- Cloud Run deployment;
- Terraform;
- antivirus or malware-scanning services;
- very large video ingestion;
- resumable or multipart provider-native uploads;
- CDN delivery.

## Related Documents

- ADR-0001: Portable Object Storage using Django Storage API
- IS-01: Storage Modernization
- IS-02: File Transport Modernization
- Storage call-site inventory
- Frontend file-flow inventory

## Implementation Status

- [x] Decision accepted.
- [ ] Multipart upload API implemented.
- [ ] Streaming download API implemented.
- [ ] Base64 upload removed.
- [ ] Presigned upload API removed.
- [ ] Presigned download API removed.
- [ ] Frontend contract updated.
