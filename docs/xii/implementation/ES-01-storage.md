# Claude Code Implementation Specification — IS-01: Portable Storage Modernization

You are working inside a maintained fork of:

```text
https://github.com/ohcnetwork/care
```

The purpose of this phase is to modernize CARE's object-storage implementation using Django's native Storage API and `django-storages`.

This is **not** a GCP-only refactor.

The resulting CARE application must remain portable and must support multiple storage profiles through configuration.

The initial supported profiles are:

```text
Local development:
Django Storage API
→ django-storages S3Storage
→ MinIO

Generic S3-compatible deployment:
Django Storage API
→ django-storages S3Storage
→ AWS S3, MinIO or another compatible provider

Initial GCP deployment:
Django Storage API
→ django-storages GoogleCloudStorage
→ Google Cloud Storage
```

Google Cloud Storage is the first managed-cloud target, but it is not the application architecture.

The application architecture is Django Storage API.

---

# 1. Current repository state

The runtime inventory and green baseline have already been completed.

The baseline commit is:

```text
755e8cb20
```

The baseline established:

- Python 3.13.14;
- Django 6.0;
- Docker and Docker Compose local runtime;
- PostgreSQL, Redis, MinIO, backend and Celery services healthy;
- 312 migrations applied;
- permissions and value sets synchronized;
- fixtures loaded;
- 1,912 tests passing in successful complete runs;
- one known pre-existing parallel-test flake related to rate limiting;
- no blocking baseline issue.

The previous inventory commit was:

```text
2fe40cd16
```

The documentation and inventories are located under:

```text
docs/xii/architecture/
docs/xii/architecture/inventory/
```

Read these files before changing code:

```text
docs/xii/architecture/00-scope-and-goals.md
docs/xii/architecture/01-current-runtime.md
docs/xii/architecture/02-target-runtime.md
docs/xii/architecture/03-migration-plan.md
docs/xii/architecture/04-testing.md
docs/xii/architecture/07-configuration-reference.md

docs/xii/architecture/inventory/storage-call-sites.md
docs/xii/architecture/inventory/frontend-file-flow.md
docs/xii/architecture/inventory/runtime-and-deployment.md
docs/xii/architecture/inventory/plugin-impact.md
docs/xii/architecture/inventory/unresolved-items.md
```

The inventories are authoritative for the current repository commit.

Verify every assumption against the current source before implementing it.

---

# 2. Branch and repository preconditions

The maintained integration branch is:

```text
gcp
```

Create or use this feature branch:

```text
feature/storage-modernization
```

Before doing any work, report:

```bash
git status
git branch --show-current
git log -5 --oneline
git remote -v
```

Verify:

- the working tree is clean;
- the current branch is `feature/storage-modernization`;
- the branch contains commit `755e8cb20`;
- `upstream` points to `https://github.com/ohcnetwork/care`;
- the branch is based on the maintained `gcp` branch.

Do not:

- reset;
- rebase;
- merge unrelated branches;
- force-push;
- push any commit.

If the current branch is incorrect, stop and report it rather than modifying Git history automatically.

---

# 3. Objective

Replace CARE's custom provider-specific object persistence with Django's Storage API using `django-storages`.

After this phase:

1. CARE file persistence must use Django storage aliases.
2. MinIO must remain the default local storage service.
3. MinIO must be accessed through `storages.backends.s3.S3Storage`.
4. Generic S3-compatible deployments must be configurable.
5. Google Cloud Storage must be configurable through `GoogleCloudStorage`.
6. Switching providers must require configuration changes only.
7. CARE application logic must not instantiate provider clients.
8. CARE storage logic must not call `boto3` for file persistence.
9. Static files must continue using WhiteNoise.
10. Existing local Docker Compose behavior must remain functional.
11. No GCP credentials may be required for local development.
12. No direct browser-upload or file-transport redesign is required in this phase.

This phase modernizes the **storage seam** only.

The next phase will modernize the HTTP file transport and remove:

- base64 uploads;
- presigned browser uploads;
- presigned browser downloads.

---

# 4. Architecture

The required architecture is:

```text
CARE models, services and API code
              |
              v
Django Storage API
              |
              v
django.core.files.storage.storages
              |
              +--------------------------------+
              |                                |
              v                                v
storages.backends.s3.S3Storage     storages.backends.gcloud.GoogleCloudStorage
              |                                |
              v                                v
MinIO / AWS S3 / compatible S3             Google Cloud Storage
```

Application code must refer to logical storage aliases:

```text
patient
facility
report
staticfiles
```

Application code must not know which provider implements an alias.

Provider selection belongs entirely in Django settings.

---

# 5. Architectural rules

## 5.1 Django Storage is the abstraction

Do not create a general-purpose storage framework.

Do not introduce:

```text
StoragePort
StorageAdapter
StorageRegistry
StorageProviderFactory
S3FilesManager plus GCSFilesManager
MinIOFilesManager
CloudStorageService
```

The abstraction already exists:

```python
django.core.files.storage.Storage
```

Use it.

## 5.2 Provider-neutral application code

Application code may use:

```python
from django.core.files.storage import storages
```

Application code must not contain provider branches such as:

```python
if settings.CARE_STORAGE_BACKEND == "gcs":
    ...
elif settings.CARE_STORAGE_BACKEND == "s3":
    ...
```

Those branches belong only in settings construction.

## 5.3 MinIO remains the local default

The local Docker Compose profile must continue using MinIO.

Its implementation changes from custom `boto3` operations to:

```text
django-storages S3Storage
```

The local stack must start without:

- Google credentials;
- GCP project identifiers;
- GCS buckets;
- service-account JSON;
- internet access to GCP.

## 5.4 GCS is additive

GCS support must be available through configuration, but it must not replace or break S3-compatible storage.

Do not make GCS variables mandatory when S3 is selected.

## 5.5 No direct bucket-upload redesign yet

Do not implement multipart API uploads in this phase.

Do not redesign frontend contracts in this phase.

Do not add signed upload support to a custom storage backend.

Do not reproduce the current presigned behavior inside subclasses of `S3Storage` or `GoogleCloudStorage`.

Current signed URL behavior may be retained temporarily in isolated legacy code only when required to preserve existing tests and API compatibility until IS-02.

---

# 6. Scope

This phase includes:

- dependency changes;
- Django storage-alias configuration;
- local MinIO through `S3Storage`;
- generic S3-compatible configuration;
- GCS configuration support;
- replacing ordinary object persistence with Django Storage operations;
- provider-neutral object-name generation;
- storage-focused tests;
- compatibility handling required to keep the current suite green;
- storage inventory updates;
- relevant documentation corrections.

This phase does not include:

- multipart upload endpoints;
- frontend changes;
- removal of all signed URL API contracts;
- Cloud Run;
- Cloud SQL;
- Cloud Tasks;
- Terraform;
- Redis changes;
- cache changes;
- lock changes;
- rate-limit fixes;
- Celery migration;
- PostgreSQL queue implementation;
- PostgreSQL cache implementation;
- domain-model redesign;
- repository pattern;
- broad architectural reorganization.

---

# 7. Allowed modifications

Claude MAY modify files directly related to:

- dependency declarations and lockfiles;
- Django storage settings;
- current CARE file-management implementation;
- storage-related helpers;
- storage-related serializers or services where required;
- storage tests;
- storage configuration tests;
- local Docker settings only when necessary to preserve MinIO;
- GCP-capable settings support;
- storage inventories and architecture documentation.

Likely areas include, but are not limited to:

```text
config/settings/
care/utils/csp/
care/emr/utils/file_manager.py
storage-related CARE models or services
storage-related tests
dependency files
lockfiles
docs/xii/architecture/
```

Claude SHALL NOT modify unrelated:

```text
patient business rules
encounter business rules
facility permissions
authentication architecture
Redis locks
rate limiting
Celery dispatch
unrelated migrations
Terraform
frontend repositories outside this checkout
```

Any modification outside the storage surface must be explicitly justified in the final report.

---

# 8. Dependency management

Inspect the repository's actual package-management files and commands.

Add a version of `django-storages` compatible with:

```text
Python 3.13
Django 6.0
the repository's dependency resolver
```

Install support for:

```text
S3
Google Cloud Storage
```

Use the dependency manager's supported extras or explicit dependencies.

Do not edit lockfiles manually.

Do not upgrade unrelated packages.

Do not remove `boto3` globally merely because storage no longer uses it.

The inventory indicates that other functionality or plugins may still require AWS libraries.

After dependency changes:

- rebuild the application image;
- verify dependency resolution;
- verify imports;
- record the exact dependency versions selected.

---

# 9. Backend-selection configuration

Implement a narrow provider-selection setting.

Preferred variable:

```text
CARE_STORAGE_BACKEND
```

Initial supported values:

```text
s3
gcs
```

Default value:

```text
s3
```

The default must preserve existing local behavior.

Invalid values must cause a clear configuration error listing supported values.

Do not introduce:

```text
IS_GCP
USE_GCP
USE_GOOGLE_STORAGE
CLOUD_PROVIDER
```

as storage-logic switches.

A future filesystem test backend may remain test-only and does not need to be exposed as a normal production option in this phase.

---

# 10. Logical storage aliases

Define these aliases in Django's `STORAGES` setting:

```text
patient
facility
report
staticfiles
```

Preserve WhiteNoise for:

```text
staticfiles
```

The object-storage aliases must be independently configurable even if two aliases use the same physical bucket.

For example, the `report` alias may use the same bucket as `patient`, but application code should still request:

```python
storages["report"]
```

This preserves logical intent and allows future independent configuration.

Do not make provider names part of alias names.

Incorrect:

```text
gcs_patient
minio_patient
s3_report
```

Correct:

```text
patient
facility
report
```

---

# 11. S3-compatible profile

When:

```text
CARE_STORAGE_BACKEND=s3
```

configure object-storage aliases using:

```text
storages.backends.s3.S3Storage
```

The profile must support:

- local MinIO;
- AWS S3;
- reasonably compatible S3 providers supported by `django-storages`.

Settings may include, as supported by the installed version:

```text
bucket_name
access_key
secret_key
endpoint_url
region_name
addressing_style
signature_version
querystring_auth
file_overwrite
default_acl
```

Use only necessary options.

## 11.1 Existing local configuration

Inspect the tracked:

```text
docker/.local.env
docker/.prebuilt.env
```

and existing settings.

Reuse current local values where practical.

Avoid requiring a new local `.env`.

Preserve:

- current MinIO service hostname;
- current local bucket names;
- existing local credentials;
- current region compatibility;
- internal Docker endpoint behavior.

External browser-facing MinIO endpoints may remain temporarily for legacy signed-URL compatibility, but must not become part of the new Django Storage persistence design.

## 11.2 Generic S3 deployment

Do not hardcode MinIO-specific behavior in application code.

`S3Storage` settings should permit the endpoint to be absent for AWS S3.

MinIO-specific options should be set through environment configuration or local settings.

---

# 12. GCS profile

When:

```text
CARE_STORAGE_BACKEND=gcs
```

configure object-storage aliases with:

```text
storages.backends.gcloud.GoogleCloudStorage
```

Use Application Default Credentials by default.

Do not require:

```text
GOOGLE_APPLICATION_CREDENTIALS
```

inside Cloud Run or other identity-aware managed environments.

Do not require a service-account JSON file.

Allow local integration tests to use standard Google credential mechanisms when explicitly configured.

Required logical bucket configuration should use provider-neutral names such as:

```text
CARE_PATIENT_STORAGE_BUCKET
CARE_FACILITY_STORAGE_BUCKET
CARE_REPORT_STORAGE_BUCKET
```

If compatibility with old environment variables is retained temporarily:

- define precedence clearly;
- prefer new provider-neutral names;
- avoid printing secret values;
- document deprecation;
- do not silently combine conflicting values.

Do not contact live GCS during ordinary local tests.

---

# 13. Storage alias construction

Avoid copying nearly identical dictionaries repeatedly when a small settings helper can construct aliases safely.

A settings-level helper may accept:

```text
logical bucket name
selected backend
provider options
```

However:

- keep the helper inside settings or configuration code;
- do not expose it as an application storage framework;
- keep the final `STORAGES` value explicit and understandable;
- preserve the existing `staticfiles` configuration.

The alias configuration must be easy to inspect in tests.

---

# 14. Object-name generation

Preserve the verified convention:

```text
<file_type>/<internal_name>
```

Verify the convention against every relevant call site.

Create one small provider-neutral helper when it removes duplicated path logic.

Example conceptual contract:

```python
def get_storage_name(file_object) -> str:
    ...
```

The helper must:

- return a relative storage name;
- not contain a bucket;
- not contain a URL;
- not contain a provider endpoint;
- normalize only what CARE actually requires;
- preserve existing names where compatibility matters.

Test:

- standard names;
- prefixes;
- Unicode;
- extensions;
- unusual but valid names;
- path traversal attempts.

Do not call private `django-storages` normalization methods from application code.

---

# 15. Map logical file types to aliases

Determine from the inventory and source how CARE distinguishes:

```text
patient
facility
report
```

Implement the smallest clear mapping.

Possible approaches include:

- model-level storage alias property;
- helper based on verified bucket type;
- explicit service selection.

Avoid hidden global inference.

Do not put provider names into models.

The mapping must be tested.

Examples of expected intent:

```text
patient upload -> storages["patient"]
facility upload -> storages["facility"]
report output -> storages["report"]
```

If reports currently share patient credentials or a physical bucket, retain that physical behavior through settings while using the logical `report` alias.

---

# 16. Replace ordinary persistence operations

Replace provider-specific CARE operations with Django Storage API.

Use operations such as:

```python
storage.save(name, content)
storage.open(name, "rb")
storage.exists(name)
storage.delete(name)
storage.size(name)
```

Where the current code writes raw bytes, use an appropriate Django file wrapper such as:

```python
from django.core.files.base import ContentFile
```

Only wrap bytes when necessary.

Where the caller already provides a Django uploaded file or file-like object, pass it through without reading all bytes first.

Use context managers for reads.

Do not depend on provider response dictionaries.

Do not return raw boto3 or Google SDK responses to CARE code.

---

# 17. Bulk deletion

Django Storage does not define a portable bulk-delete API.

Replace batch provider calls with safe iteration:

```python
for name in names:
    storage.delete(name)
```

Preserve current cleanup semantics.

Determine whether current behavior:

- ignores missing objects;
- stops on first provider failure;
- continues after failure;
- reports failed names.

Implement and test the intended behavior.

Do not add provider-specific batch optimization during this phase.

A future optimization may be considered only after profiling demonstrates a real bottleneck.

---

# 18. Reads and memory use

Inspect every current `file_contents` or equivalent caller.

Classify each as:

```text
requires bytes
can consume a file-like object
can stream
unknown
```

Prefer:

```python
with storage.open(name, "rb") as file:
    ...
```

Do not read entire objects into memory without a verified need.

Where report generation or another internal library requires complete bytes, retain that behavior only at that call site and document it.

This phase does not need to redesign report-generation libraries.

Update the inventory with remaining whole-file reads.

---

# 19. Missing objects and errors

Provider-specific exceptions must not leak into migrated consumers.

Do not build a large custom exception hierarchy.

Use:

- standard Django Storage behavior;
- `FileNotFoundError` where appropriate;
- existing CARE API exceptions where already defined;
- narrowly translated errors only when required.

Preserve verified API behavior for missing objects.

Tests must cover:

- object exists;
- object missing;
- storage write failure;
- storage read failure;
- storage deletion failure.

Do not expose provider credential or bucket details in user-facing errors.

---

# 20. Existing `files_manager` compatibility

The inventory identifies multiple consumers of:

```text
files_manager
S3FilesManager
```

Choose the least invasive safe path.

Preferred order:

1. Migrate a caller directly to the relevant Django storage alias when the patch is small and clear.
2. Retain a thin compatibility wrapper only when direct migration would create excessive unrelated changes.

A compatibility wrapper may expose existing ordinary CRUD-shaped methods.

It must:

- resolve a logical storage alias;
- generate a provider-neutral object name;
- delegate to Django Storage;
- contain no provider SDK imports;
- contain no provider-specific branches;
- return provider-neutral values;
- be marked transitional where applicable.

It must not:

- generate presigned uploads;
- generate presigned downloads through new storage subclasses;
- recreate `boto3` semantics;
- expose raw provider clients;
- become the new permanent storage abstraction.

Signed URL legacy behavior must be separated from ordinary persistence behavior.

---

# 21. Signed URL compatibility boundary

Current CARE exposes presigned storage flows.

The final architecture forbids direct browser-to-bucket upload and normal direct bucket download.

That final removal belongs to IS-02.

For IS-01:

1. Identify every remaining signed-upload caller.
2. Identify every remaining signed-download caller.
3. Separate signed-URL behavior from ordinary CRUD.
4. Do not add signed URL methods to Django storage subclasses.
5. Do not add custom provider-specific storage backends.
6. Preserve existing behavior only as narrowly as needed to keep the current public API and tests functioning.
7. Clearly mark legacy paths and exact callers.
8. Ensure all non-signed storage persistence already uses Django Storage.
9. Update the frontend-flow inventory with what remains for IS-02.

If current tests permit removing a signed path without frontend work, it may be removed, but do not broaden the scope merely to remove it.

No new feature may depend on the legacy signed URL path.

---

# 22. Existing base64-through-Django upload

The inventory established that CARE already has a Django-proxied upload endpoint using base64.

Do not redesign it in IS-01.

Only change its underlying persistence to use Django Storage where appropriate.

Do not convert it to multipart yet.

Document:

- whether it reads complete content into memory;
- which alias it uses;
- which next-phase changes are required.

IS-02 will replace base64 transport with `multipart/form-data` and Django upload handlers.

---

# 23. Static files

Preserve:

```text
whitenoise.storage.CompressedManifestStaticFilesStorage
```

Do not move static files to MinIO or GCS.

Do not alter static URL behavior unless dependency changes require a minimal compatibility adjustment.

Verify:

```bash
python manage.py collectstatic --noinput
```

continues to work.

---

# 24. File overwrite and duplicate names

Django Storage backends may rename duplicate object names unless overwrite behavior is configured.

Inspect CARE's current assumptions.

Determine whether CARE expects:

- unique generated internal names;
- overwrite;
- duplicate prevention;
- automatic renaming.

Do not assume the same behavior across MinIO and GCS.

Set backend options only after verifying expected semantics.

Add tests that assert CARE-level behavior, not provider internals.

If internal names are already unique, document that and avoid unnecessary overwrite customization.

---

# 25. ACL and public-access policy

No object-storage alias should require public objects.

For GCS configuration:

- prefer uniform bucket-level access;
- do not configure public-read defaults;
- do not rely on object ACLs.

For S3-compatible configuration:

- avoid public default ACLs;
- keep access private unless current local tests require otherwise;
- do not expose provider URLs as the new application contract.

This phase does not implement cloud IAM or Terraform.

It only ensures storage settings are compatible with private buckets.

---

# 26. Configuration compatibility

The greenfield cloud configuration should use provider-neutral variables.

Local tracked settings must continue to work.

Where practical, support existing variables temporarily.

Do not require users to rewrite all local configuration just to preserve MinIO.

New variable precedence should be:

1. explicit provider-neutral variable;
2. unambiguous existing compatibility variable;
3. safe local default where already established;
4. clear error.

If old settings contain a verified bug—for example, credentials read from an unexpected variable set—do not preserve the bug blindly.

Correct it with tests and document the behavior change.

Do not expand this into a broad settings rewrite.

---

# 27. Test strategy

Add focused tests before or alongside implementation.

Follow existing CARE test conventions.

## 27.1 Settings tests

Test:

```text
default backend is s3
s3 aliases use S3Storage
gcs aliases use GoogleCloudStorage
patient alias resolves
facility alias resolves
report alias resolves
staticfiles remains WhiteNoise
invalid backend is rejected
GCS variables are not required under s3
S3 variables are not required under gcs except compatibility as designed
```

Do not instantiate real GCS clients in basic settings tests if credentials would be required.

## 27.2 Object-name tests

Test:

- expected key format;
- patient object;
- facility object;
- report object;
- Unicode;
- extension handling;
- path traversal or invalid path behavior.

## 27.3 Storage behavior tests

Test through Django Storage abstractions:

```text
save
open
exists
delete
missing object
content preservation
duplicate-name semantics
logical alias selection
```

## 27.4 Compatibility wrapper tests

If a wrapper remains, prove it delegates through Django Storage.

Use test storage backends or mocks at the Django Storage boundary.

Do not mock `boto3` in new persistence tests.

## 27.5 MinIO integration tests

Run real integration tests against the current local MinIO container.

Verify:

- aliases connect;
- write succeeds;
- read succeeds;
- deletion succeeds;
- missing-object behavior is controlled;
- local Docker workflow remains unchanged.

This is a mandatory profile.

## 27.6 GCS configuration tests

Verify GCS aliases are constructed correctly without requiring a live GCP project.

An optional live GCS integration test may be created with an explicit marker or skip condition.

Ordinary local tests must not require Google credentials.

## 27.7 Static-import verification

Search migrated CARE storage modules for:

```text
boto3
botocore
google.cloud.storage
```

There must be no direct provider client use for migrated file persistence.

Do not prohibit these imports globally if other verified integrations require them.

## 27.8 Existing API regression

Run all existing file API tests.

Signed URL and base64 tests may remain in this phase if compatibility paths remain.

Do not weaken tests merely to make the refactor pass.

---

# 28. Baseline and full regression

After focused tests pass, execute the official Docker-based workflow.

Use the exact commands recorded in:

```text
docs/xii/architecture/inventory/runtime-and-deployment.md
```

Because dependencies change, rebuild the image.

Verify:

- PostgreSQL healthy;
- Redis healthy;
- MinIO healthy;
- Celery healthy;
- backend healthy;
- migrations succeed;
- permission synchronization succeeds;
- value-set synchronization succeeds;
- fixtures succeed;
- static collection succeeds;
- complete suite runs with the same parallel and shuffle configuration.

Record:

```text
seed
test count
pass count
fail count
skip count
warnings
test duration
wall duration
```

The known E7 rate-limit flake may appear.

If E7 appears:

1. record the seed;
2. run that test in isolation;
3. run the complete suite once more with a new seed;
4. do not fix E7 in this branch;
5. ensure no storage failure is mislabeled as E7.

A deterministic storage failure must be fixed before completion.

---

# 29. Documentation updates

Update:

```text
docs/xii/architecture/inventory/storage-call-sites.md
```

For each call site, mark:

```text
migrated_to_django_storage
legacy_signed_url_only
temporary_wrapper
not_storage_persistence
blocked
```

Update:

```text
docs/xii/architecture/inventory/frontend-file-flow.md
```

Record:

- base64 upload flow remaining;
- signed upload flow remaining;
- signed download flow remaining;
- which persistence operations now use Django Storage;
- exact scope required for IS-02.

Update:

```text
docs/xii/architecture/inventory/unresolved-items.md
```

only with real unresolved storage issues.

Correct architecture documents so they explicitly state:

```text
Django Storage API is the architecture.
MinIO through S3Storage is the default local profile.
Generic S3-compatible storage remains supported.
GCS is the initial GCP storage profile, not the only supported provider.
```

Do not rewrite unrelated task, cache, Redis or Terraform sections.

---

# 30. Required implementation deliverables

This phase should produce, as applicable:

```text
django-storages dependency configuration
S3 and GCS backend dependencies
provider-selectable STORAGES configuration
patient storage alias
facility storage alias
report storage alias
preserved staticfiles alias
provider-neutral object-name helper
migrated ordinary storage CRUD
thin compatibility wrapper only where necessary
storage configuration tests
storage behavior tests
MinIO integration tests
GCS configuration tests
updated inventories
updated architecture wording
```

---

# 31. Prohibited work

Do not:

- implement multipart uploads;
- change frontend code;
- remove every signed URL endpoint if doing so requires the next transport phase;
- subclass storage backends merely to create signed uploads;
- introduce a custom GCS manager;
- introduce a custom S3 manager as a new primary abstraction;
- make GCP mandatory;
- require GCP credentials locally;
- remove MinIO;
- remove Celery;
- change Redis;
- fix locks;
- fix E7 rate limiting;
- add PostgreSQL cache;
- add PostgreSQL queues;
- add Cloud Tasks;
- add Cloud Run;
- add Cloud SQL infrastructure;
- add Terraform;
- change domain models for architectural purity;
- add repository patterns;
- reorganize CARE applications;
- push commits.

---

# 32. Commit strategy

Use focused commits.

Recommended sequence:

```text
chore(storage): add django-storages backends
feat(storage): configure portable storage aliases
refactor(storage): route file persistence through Django Storage
test(storage): cover aliases and MinIO integration
docs(storage): update modernization inventory
```

The exact sequence may differ if repository mechanics make another grouping clearer.

Avoid a single giant commit.

Do not push.

---

# 33. Acceptance criteria

IS-01 is complete only when all of the following are true:

- `CARE_STORAGE_BACKEND` supports `s3` and `gcs`;
- `s3` is the default;
- local Docker uses MinIO through `S3Storage`;
- local startup requires no GCP values;
- GCS aliases can be configured through `GoogleCloudStorage`;
- patient, facility and report aliases are provider-neutral;
- static files remain on WhiteNoise;
- ordinary CARE storage persistence uses Django Storage;
- migrated modules no longer instantiate `boto3`;
- no manual GCS persistence implementation exists;
- provider switching requires settings changes only;
- MinIO integration tests pass;
- GCS configuration tests pass;
- the full CARE suite passes, subject only to the documented E7 flake procedure;
- remaining signed URL paths are precisely documented for IS-02;
- remaining base64 transport is precisely documented for IS-02;
- the branch contains no Redis, task, lock or GCP deployment changes.

---

# 34. Final report

At completion, report:

1. current branch;
2. initial and final commit;
3. commits created;
4. dependencies added and resolved versions;
5. files created;
6. files modified;
7. storage-selection configuration;
8. aliases implemented;
9. local MinIO behavior;
10. generic S3-compatible behavior;
11. GCS configuration behavior;
12. ordinary legacy CRUD removed;
13. direct `boto3` persistence imports remaining and exact reasons;
14. compatibility wrapper remaining and exact callers;
15. signed upload paths remaining;
16. signed download paths remaining;
17. base64 upload path remaining;
18. whole-file memory reads remaining;
19. MinIO integration-test results;
20. GCS configuration-test results;
21. full test results with seeds and counts;
22. whether E7 occurred;
23. documentation updated;
24. unresolved storage issues;
25. exact recommended scope for IS-02 File Transport Modernization.

Stop after IS-01.

Do not begin IS-02.
