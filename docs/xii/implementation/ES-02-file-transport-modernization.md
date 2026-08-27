# ES-02: File Transport Modernization

- **Status:** Draft
- **Related ADR:** ADR-0002: Server-Mediated File Transport
- **Depends on:** ADR-0001 and completed ES-01
- **Target branch:** `feature/file-transport-modernization`

---

# 1. Context

ES-01 completed the storage modernization.

The current storage architecture is now:

```text
CARE
  ↓
Django Storage API
  ↓
django-storages
  ├── S3Storage → MinIO / S3-compatible providers
  └── GoogleCloudStorage → GCS
```

All object-storage persistence is provider-neutral.

Signed upload and download URLs have been removed.

Downloads now pass through CARE using Django and `FileResponse`.

The remaining transport issue is the current upload contract.

CARE still contains an upload flow in which file content is sent to Django as
base64-encoded data.

That flow now persists correctly through Django Storage, but the HTTP transport
itself remains inefficient.

The target of this phase is therefore narrowly defined:

```text
base64-over-JSON upload
        ↓
multipart/form-data upload
        ↓
Django UploadedFile / upload handlers
        ↓
Django Storage API
```

This phase does not change the storage architecture established by ES-01.

---

# 2. Repository State

Before implementation, verify the current repository state.

The active branch MUST be:

```text
feature/file-transport-modernization
```

The branch MUST be based on the current `gcp` branch containing the merged and
completed ES-01 implementation.

Before modifying code, report:

```bash
git status
git branch --show-current
git log -5 --oneline
git remote -v
```

Verify:

- the working tree is clean;
- `gcp` contains completed ADR-0001 / ES-01;
- `upstream` points to `https://github.com/ohcnetwork/care`;
- no unrelated local commits are present.

Do not reset, rebase, merge unrelated work or push automatically.

---

# 3. Required Documents

Read these documents before implementation:

```text
docs/xii/architecture/00-scope-and-goals.md
docs/xii/architecture/01-current-runtime.md
docs/xii/architecture/02-target-runtime.md
docs/xii/architecture/03-migration-plan.md
docs/xii/architecture/04-testing.md
docs/xii/architecture/07-configuration-reference.md

docs/xii/adr/ADR-0001-django-storage.md
docs/xii/adr/ADR-0002-file-transport.md

docs/xii/implementation/ES-01-storage.md

docs/xii/architecture/inventory/storage-call-sites.md
docs/xii/architecture/inventory/frontend-file-flow.md
docs/xii/architecture/inventory/unresolved-items.md
```

If the repository uses different final paths, locate the actual committed files
and use those.

The ADR defines the architectural decision.

This ES defines the implementation requirements.

The current source code is authoritative for implementation details.

---

# 4. Objective

Replace CARE's remaining base64-based file upload transport with normal HTTP
multipart upload handling.

After this phase:

- file uploads use `multipart/form-data`;
- Django receives files as `UploadedFile` objects;
- Django upload handlers determine memory vs temporary-file behavior;
- the complete uploaded file is not base64-encoded;
- the API does not require complete file content inside JSON;
- object persistence continues through Django Storage;
- downloads continue through CARE and Django Storage;
- no provider URL is returned to clients;
- no browser communicates directly with object storage;
- MinIO, S3-compatible storage and GCS all use the same HTTP API;
- upload validation and authorization remain centralized in CARE.

This phase modernizes **HTTP file transport only**.

---

# 5. Target Architecture

The upload path SHALL become:

```text
Client
  |
  | multipart/form-data
  v
CARE Django API
  |
  | request.FILES / UploadedFile
  v
CARE validation and authorization
  |
  v
Django Storage API
  |
  v
Configured storage backend
```

The download path remains:

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
FileResponse
```

The HTTP contract SHALL remain provider-independent.

---

# 6. Scope

This phase includes:

- replacing base64 file payloads;
- multipart request parsing;
- Django `UploadedFile` handling;
- upload size configuration;
- validation of upload metadata;
- preserving existing authorization semantics;
- preserving existing object naming;
- preserving provider-neutral storage aliases;
- updating API schemas;
- updating backend tests;
- updating frontend-facing API contracts in this repository where applicable;
- removal of obsolete base64 transport code;
- removal of obsolete upload DTO/schema fields;
- documentation updates.

This phase does not include:

- Cloud Tasks;
- Celery migration;
- retry redesign;
- Redis;
- cache;
- locks;
- rate-limit fixes;
- Cloud Run;
- Cloud SQL;
- Terraform;
- CI/CD;
- provider-native multipart upload;
- signed URLs;
- CDN design;
- resumable uploads;
- antivirus scanning;
- large-video ingestion architecture.

---

# 7. Out of Scope

Do not:

- reintroduce signed URLs;
- expose bucket URLs;
- expose storage-provider names;
- implement browser-to-bucket uploads;
- redesign Django Storage;
- create a new upload abstraction layer;
- modify unrelated models;
- modify task execution;
- modify Redis configuration;
- fix E7;
- change report-generation retry behavior;
- add cloud deployment resources.

Remain strictly inside file transport.

---

# 8. Design Rules

## 8.1 Django owns HTTP upload parsing

Use Django and Django REST Framework's normal multipart support.

Do not manually parse multipart bodies.

Do not decode the complete upload manually.

Use:

```text
request.FILES
UploadedFile
TemporaryUploadedFile
InMemoryUploadedFile
```

or the repository's existing DRF equivalents.

## 8.2 Django Storage remains the persistence boundary

After receiving and validating the `UploadedFile`, persistence SHALL continue
through the provider-neutral storage seam created by ES-01.

No transport code may instantiate:

- boto3;
- GCS clients;
- MinIO clients;
- provider SDKs.

## 8.3 No base64 file transport

The target upload API SHALL not accept file content encoded as base64.

Any current field containing complete file content as:

```text
base64
data URL
encoded JSON string
```

shall be removed from the final production upload contract.

## 8.4 No provider-specific transport behavior

Upload behavior SHALL be identical for:

```text
MinIO
AWS S3
generic S3-compatible storage
Google Cloud Storage
```

Provider switching must remain configuration-only.

---

# 9. Current Upload Flow Inventory

Before changing code, inspect the exact current base64 upload flow identified by
the ES-01 inventory.

Document:

- endpoint path;
- viewset or API function;
- serializer or request schema;
- base64 field name;
- metadata fields;
- authorization path;
- object-name generation;
- storage alias selection;
- model updates;
- response schema;
- frontend or tests that call it.

Verify whether more than one base64 upload path exists.

Do not assume there is only one because the inventory previously identified one.

Update the inventory if the source has changed.

---

# 10. Multipart API Contract

The upload endpoint SHALL accept:

```text
Content-Type: multipart/form-data
```

The request SHALL contain one uploaded file field.

Preferred field name:

```text
file
```

If the current CARE API already uses another established field name and changing
it would create unnecessary compatibility work, preserve the established name.

Metadata SHOULD remain ordinary multipart fields.

Examples may include:

```text
file_type
name
patient
facility
encounter
metadata
```

Only verified current fields SHALL be preserved.

Do not create speculative metadata fields.

---

# 11. Serializer / Request Validation

Use DRF's file-aware serializer fields where appropriate.

Prefer:

```python
serializers.FileField()
```

or equivalent project-native request schema support.

Validation SHALL occur before persistence when possible.

Validate:

- file presence;
- maximum size;
- extension;
- allowed MIME type;
- logical file type;
- related object identifiers;
- authorization;
- filename safety.

Do not trust browser-provided MIME type as the only source of truth when CARE
already has stronger validation logic.

Preserve existing validation behavior unless the base64 implementation itself
prevented correct validation.

---

# 12. File Size Limits

Explicit file-size limits SHALL be defined.

The implementation SHALL inspect current CARE limits before introducing new
ones.

The relevant settings may include:

```text
CARE_MAX_UPLOAD_SIZE
FILE_UPLOAD_MAX_MEMORY_SIZE
DATA_UPLOAD_MAX_MEMORY_SIZE
```

The actual names must match the configuration reference.

The implementation SHALL ensure:

- small supported files may remain in memory;
- larger supported files use Django temporary-file handling;
- unsupported oversized files are rejected cleanly;
- the application does not base64-decode large payloads into memory;
- Cloud/runtime-specific limits are not hardcoded in domain code.

Do not invent an arbitrary maximum if CARE already defines one.

If no maximum exists, add an explicit conservative setting and document it.

---

# 13. Temporary Files

Django may store larger uploads in temporary files.

Temporary files SHALL:

- use Django's normal upload-handler lifecycle;
- remain ephemeral;
- not become durable storage;
- be closed after use;
- not be manually copied unless required.

Cloud or local runtime filesystem behavior SHALL not leak into application
semantics.

The implementation MAY configure:

```text
FILE_UPLOAD_TEMP_DIR=/tmp
```

only if necessary.

Do not assume `/tmp` is durable.

---

# 14. Storage Save Path

The upload implementation SHALL pass the Django uploaded-file object or
file-like object directly to the relevant storage implementation where possible.

Preferred conceptual behavior:

```python
uploaded_file = serializer.validated_data["file"]

stored_name = storage.save(
    object_name,
    uploaded_file,
)
```

Do not do:

```python
content = uploaded_file.read()
storage.save(name, ContentFile(content))
```

unless a verified downstream requirement forces a complete read.

Avoid unnecessary memory copies.

---

# 15. Object Naming

Object naming SHALL remain exactly compatible with ES-01.

The existing provider-neutral object-name helper remains authoritative.

The HTTP upload phase SHALL not create a second naming function.

Object names remain storage-relative and provider-neutral.

Do not include:

- bucket names;
- endpoints;
- URLs;
- provider prefixes.

---

# 16. Logical Storage Alias Selection

Upload transport SHALL continue selecting the appropriate logical alias:

```text
patient
facility
report
```

The transport layer SHALL not inspect `CARE_STORAGE_BACKEND`.

Alias selection is based on CARE domain intent, not infrastructure.

Tests must prove that multipart transport does not alter alias selection.

---

# 17. Authorization

Preserve CARE's existing upload authorization model.

The new multipart endpoint SHALL not weaken:

- patient access;
- facility access;
- encounter access;
- ownership checks;
- role checks;
- organization boundaries.

The transport modernization SHALL not redesign authorization logic.

Existing authorization tests SHALL continue to pass.

Add focused tests if current base64 tests did not verify authorization
adequately.

---

# 18. Database and Storage Consistency

Object storage and PostgreSQL do not share an atomic transaction.

The implementation SHALL preserve or improve the current failure behavior.

Analyze the current sequence:

```text
validate
save object
write DB
```

or:

```text
write DB
save object
```

Document the actual current behavior.

Handle partial failures explicitly.

At minimum:

- storage failure must not report successful upload;
- database failure after storage save must not leave an undetectable completed
  record;
- existing cleanup behavior must remain compatible;
- incomplete-object cleanup logic must still work.

Do not introduce a complex distributed transaction framework.

Use the smallest correct compensation behavior.

---

# 19. Response Contract

The successful upload response SHALL remain provider-neutral.

It MAY include:

- CARE object identifier;
- metadata;
- relative CARE `download_url`;
- filename;
- MIME type;
- size;
- status.

It SHALL NOT include:

- bucket URL;
- S3 URL;
- GCS URL;
- signed URL;
- storage credentials;
- provider-specific object metadata unless CARE already exposes it for a valid
  reason.

If the previous base64 endpoint returned provider details, remove them.

---

# 20. Downloads

ES-01 already implemented server-mediated downloads.

Preserve them.

Do not re-architect download transport unless a defect is discovered.

Verify that upload-generated objects can be downloaded through:

```text
/files/{id}/download/
/template_reports/{id}/download/
/assets/facility/{id}/cover_image/
/assets/user/{username}/profile_picture/
```

or the actual committed equivalents.

The new multipart upload must integrate cleanly with those routes.

---

# 21. Content-Disposition

Preserve existing inline vs attachment behavior.

Do not broaden `SAFE_INLINE_FORMATS` without a verified requirement.

Filename handling must remain safe against header injection.

Tests should cover representative inline and attachment formats.

---

# 22. MIME Types

Preserve existing CARE MIME validation where possible.

The implementation SHALL distinguish:

```text
request-declared MIME
validated MIME
response MIME
```

The browser-declared MIME type SHALL not automatically be treated as trusted.

If the existing base64 endpoint used extension-only validation, preserve
behavior first unless the ADR or current security policy explicitly requires
stronger validation.

Do not introduce heavyweight file-inspection dependencies in this phase without
a demonstrated requirement.

---

# 23. Base64 Removal

Once the multipart path is verified, remove:

- base64 decoding logic;
- base64 request fields;
- base64-specific validators;
- data-URL parsing code;
- documentation describing base64 upload;
- tests whose sole purpose is preserving the old transport.

Do not retain a hidden base64 fallback.

This is a greenfield deployment.

There is no production client that requires compatibility.

---

# 24. API Schema

Update the API/OpenAPI schema so the upload request is represented as a file
upload.

The generated schema SHOULD show:

```text
multipart/form-data
```

and the correct binary file field.

Remove base64-body documentation.

Verify the schema generator does not emit the old JSON contract.

---

# 25. Frontend Contract

If frontend code is included in this repository and directly consumes the
upload endpoint, update it.

The client SHALL:

- send `FormData`;
- append the file object;
- include required metadata fields;
- call the CARE endpoint;
- consume CARE's provider-neutral response;
- never contact object storage.

If the frontend is outside this repository, document the exact API contract
change instead of inventing or modifying external code.

Do not restore compatibility solely to avoid frontend coordination.

---

# 26. Cover Images and Profile Pictures

ES-01 already moved cover-image and profile-picture downloads behind CARE.

Inspect whether their upload path also uses the base64 endpoint.

If yes, migrate it to multipart through the same provider-neutral API or the
smallest existing specialized endpoint.

Do not create duplicated upload transport logic.

If those assets already use ordinary multipart handling, leave them unchanged
and document that fact.

---

# 27. Report Files

Do not modify report-generation retry policy in this phase.

The existing storage-adjacent:

```text
botocore.ClientError
```

in `report_generation.py` remains assigned to ES-03.

This phase may verify that generated reports remain downloadable after upload
transport changes, but SHALL not change Celery retry behavior.

---

# 28. E7

The documented E7 parallel-test defect remains out of scope.

Do not fix:

- rate-limit cache keys;
- Redis cache clearing;
- test worker prefixes;
- favorites cache behavior.

When interpreting parallel test failures, follow the existing E7 procedure.

A deterministic transport or storage failure must not be classified as E7.

---

# 29. Allowed Modifications

Claude MAY modify:

- upload viewsets;
- upload serializers;
- upload request schemas;
- upload helpers;
- upload tests;
- API schema tests;
- provider-neutral file transport helpers;
- settings related to upload size;
- frontend code in this repository if it calls the changed endpoint;
- file-flow inventory;
- ADR-0002 implementation checklist;
- ES-02 documentation;
- configuration reference where actual upload settings change.

Claude MAY remove:

- base64 transport code;
- base64-specific tests;
- base64-specific schema fields;
- obsolete upload compatibility code.

---

# 30. Forbidden Modifications

Claude SHALL NOT modify:

- Redis configuration;
- rate limiting;
- distributed locks;
- Celery dispatch architecture;
- Cloud Tasks;
- Cloud Run;
- Cloud SQL;
- Terraform;
- CI/CD;
- unrelated domain models;
- Django ORM architecture;
- report retry behavior;
- SMS boto3 integration;
- storage provider architecture established in ES-01.

No migrations should be required unless the current base64 representation is
stored in the database, which must be verified before any migration is added.

Do not add a migration merely because an API serializer changed.

---

# 31. Tests — Focused

Add focused multipart tests.

At minimum:

## Successful upload

- valid authenticated request;
- authorized caller;
- multipart file;
- correct logical alias;
- correct object name;
- storage save succeeds;
- DB record is correct;
- response is provider-neutral;
- download works.

## Missing file

Reject multipart requests without the file field.

## Oversized file

Reject files above the configured maximum.

## Extension validation

Test:

- allowed;
- blocked;
- uppercase;
- double extension where relevant.

## MIME validation

Test:

- accepted MIME;
- mismatched MIME;
- missing MIME;
- unsafe MIME.

## Authorization

Test unauthorized upload attempts against the appropriate CARE scope.

## Temporary-file path

Add at least one test with a file larger than:

```text
FILE_UPLOAD_MAX_MEMORY_SIZE
```

using a test-specific low threshold where necessary.

Verify the handler receives a temporary-file-backed upload where the framework
supports deterministic testing.

Do not depend on huge test fixtures.

## Storage failures

Simulate:

- save failure;
- DB failure after save where applicable.

Verify consistent cleanup or explicit incomplete-state handling.

## Response

Assert no response contains:

```text
signed_url
read_signed_url
bucket
endpoint
provider URL
```

unless `bucket` is a legitimate unrelated domain field.

---

# 32. MinIO Integration

Run the multipart upload flow against real local MinIO through `S3Storage`.

Verify:

```text
multipart request
→ Django
→ S3Storage
→ MinIO
→ download through Django
```

Test at least one complete round trip.

MinIO remains the mandatory local integration profile.

---

# 33. GCS Configuration / Provider-Neutral Tests

Ordinary local tests must not require live GCS.

Use configuration or test storage to prove:

- multipart code does not branch on provider;
- alias selection remains identical under `gcs`;
- transport code receives Django Storage objects;
- no S3 assumptions remain.

If an optional live GCS test already exists from ES-01, extend it only if
credentials are available.

Do not make live GCS mandatory for the normal test suite.

---

# 34. API Schema Tests

Verify the generated API schema for the upload endpoint declares:

```text
multipart/form-data
```

and a binary/file field.

Assert the old base64 field is absent.

If CARE uses typed OpenAPI request/response specs, update them consistently.

---

# 35. Regression Tests

After focused tests pass:

1. rebuild the image if dependencies or runtime settings changed;
2. start the official local stack;
3. verify all services healthy;
4. run migrations;
5. verify permission and value-set synchronization;
6. run fixtures as appropriate;
7. run the full serial suite;
8. run the documented parallel suite.

Record:

```text
seed
test count
pass count
failure count
skip count
test duration
wall duration
```

The serial full suite must be green.

Parallel failures may be accepted only when they are demonstrated to belong to
the already documented E7 defect class.

No transport-related deterministic failure is acceptable.

---

# 36. Performance Sanity Check

This phase does not require a benchmark suite, but it SHALL verify that the new
multipart path avoids base64 expansion.

For one representative test file, record or verify qualitatively:

```text
old transport:
JSON + base64

new transport:
multipart binary
```

Do not introduce a performance framework.

The implementation should not materialize duplicate full-size byte buffers.

---

# 37. Documentation Updates

Update:

```text
docs/xii/architecture/inventory/frontend-file-flow.md
```

to mark:

```text
base64 upload -> removed
multipart upload -> implemented
server-mediated download -> implemented
signed upload -> removed
signed download -> removed
```

Update:

```text
docs/xii/architecture/inventory/storage-call-sites.md
```

only if transport changes affect documented call sites.

Update:

```text
docs/xii/adr/ADR-0002-file-transport.md
```

implementation checklist.

Update the configuration reference for final upload-size settings.

Update API documentation where the request contract changes.

Do not modify unrelated ADRs.

---

# 38. Commit Strategy

Use small logical commits.

Recommended sequence:

```text
refactor(files): replace base64 upload with multipart transport

test(files): cover multipart upload and provider-neutral round trips

docs(files): complete file transport modernization
```

If API schema and frontend changes are substantial, they may be separate
focused commits.

Do not create a giant mixed commit.

Do not squash.

Do not push.

---

# 39. Acceptance Criteria

ES-02 is complete only when all of the following are true:

- upload uses `multipart/form-data`;
- Django receives an `UploadedFile`;
- complete file content is no longer base64-encoded;
- base64 upload fields and decoder code are removed;
- uploads pass through CARE;
- downloads pass through CARE;
- Django Storage remains the only persistence boundary;
- no provider URL is returned;
- no browser-to-bucket transport exists;
- MinIO round-trip upload/download passes;
- GCS profile requires no transport-specific code;
- provider switching remains configuration-only;
- upload size limits are explicit;
- larger supported uploads use Django temporary-file behavior where applicable;
- authorization remains intact;
- file validation remains intact;
- API schema reflects multipart upload;
- frontend contract is updated or precisely documented;
- serial full regression is green;
- no deterministic file-transport regression remains;
- ADR-0002 implementation checklist is updated.

---

# 40. Final Report

At completion provide:

1. branch;
2. initial and final commit;
3. commits created;
4. files created;
5. files modified;
6. files deleted;
7. old base64 endpoint behavior;
8. final multipart endpoint contract;
9. serializer/request-schema changes;
10. upload size configuration;
11. temporary-file behavior;
12. authorization behavior;
13. validation behavior;
14. database/storage consistency handling;
15. MinIO round-trip result;
16. GCS/provider-neutral test result;
17. API schema result;
18. frontend changes or documented external contract;
19. focused test counts;
20. serial full-suite result;
21. parallel result and any E7 occurrences;
22. documentation updated;
23. unresolved file-transport items;
24. deviations from ADR-0002 or ES-02;
25. final verdict:

```text
READY TO MERGE
```

or:

```text
NOT READY TO MERGE
```

Stop after ES-02.

Do not begin ES-03.
