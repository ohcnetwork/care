---
title: Storage Call-Site Inventory
document: inventory/storage-call-sites
version: 0.2.0
status: Draft
phase: 1
source_repository: https://github.com/ohcnetwork/care
source_branch: gcp
source_commit: 6a2976dc2512c2c532fcc70628c5690fbbbe3f3d
reviewed: 2026-08-06
---

# Storage Call-Site Inventory

Every object-storage call site in the repository, enumerated.

Sections 1-8 are the Phase 0 snapshot, recorded before any storage code was
modified. **Section 11 records what IS-01 changed** and marks the migration
status of every call site. Where the two disagree, section 11 is current.

Evidence labels used throughout:

- **verified** — read directly from the file at the stated line.
- **inferred** — deduced from surrounding code; not directly asserted anywhere.
- **unknown** — cannot be determined from this repository alone.

---

## 1. Summary

**verified** The entire object-storage surface is 4 source files:

| File | Role |
| --- | --- |
| `care/emr/utils/file_manager.py` | The only S3 abstraction (`S3FilesManager`) |
| `care/utils/csp/config.py` | Credential/endpoint/bucket resolution |
| `care/utils/file_uploads/cover_image.py` | Direct `boto3` use, bypasses `S3FilesManager` |
| `config/settings/base.py` | Bucket settings |

**verified** Total distinct storage call sites: **19** (counted in §3).

**verified** `boto3` is imported in exactly 3 non-test modules:
`care/emr/utils/file_manager.py:3`, `care/utils/file_uploads/cover_image.py:5`,
and `care/utils/sms/backend/sns.py:8` (SNS, not storage — out of scope).

---

## 2. Bucket topology

**verified** `care/utils/csp/config.py:27-30` defines three logical bucket types:

```
BucketType.PATIENT
BucketType.FACILITY
BucketType.REPORT
```

**verified** These map to only **two** physical buckets
(`care/utils/csp/config.py:33-70`):

| BucketType | Physical bucket setting | Resolver | Line |
| --- | --- | --- | --- |
| `FACILITY` | `settings.FACILITY_S3_BUCKET` | `get_facility_bucket_config` | `config.py:43` |
| `PATIENT` | `settings.FILE_UPLOAD_BUCKET` | `get_patient_bucket_config` | `config.py:56` |
| `REPORT` | `settings.FILE_UPLOAD_BUCKET` | `get_report_bucket_config` | `config.py:70` |

**verified** `REPORT` and `PATIENT` resolve to the *same* physical bucket. This is
intentional and documented in the docstring at `config.py:60`:
`"""Get bucket configuration for reports - uses same bucket as patient files"""`.

### 2.1 Defect: patient/report buckets use facility credentials

**verified** `get_patient_bucket_config` (`config.py:46-56`) and
`get_report_bucket_config` (`config.py:59-70`) read
`FACILITY_S3_REGION`, `FACILITY_S3_KEY` and `FACILITY_S3_SECRET` —
not the `FILE_UPLOAD_*` equivalents:

```python
# care/utils/csp/config.py:46-56
def get_patient_bucket_config(external) -> tuple[ClientConfig, BucketName]:
    params = {"region_name": settings.FACILITY_S3_REGION}      # line 47
    if CSProvider.AWS_ROLE_BASED.value != settings.BUCKET_PROVIDER:
        params["aws_access_key_id"] = settings.FACILITY_S3_KEY     # line 49
        params["aws_secret_access_key"] = settings.FACILITY_S3_SECRET  # line 50
        ...
    return params, settings.FILE_UPLOAD_BUCKET                   # line 56
```

**verified** Consequence: `FILE_UPLOAD_REGION` (`base.py:537`),
`FILE_UPLOAD_KEY` (`base.py:538`) and `FILE_UPLOAD_SECRET` (`base.py:539`) are
defined but **read by no code in this repository**. A repository-wide grep for
each of those three names returns only their definition lines.

**verified** The endpoint settings are *not* affected — `config.py:52-55` and
`config.py:66-69` correctly use `FILE_UPLOAD_BUCKET_ENDPOINT` /
`FILE_UPLOAD_BUCKET_EXTERNAL_ENDPOINT`.

**Migration consequence (inferred):** separate credentials per bucket cannot be
configured today. Any GCP design that assumes distinct service accounts or HMAC
keys per bucket must fix `config.py` first, or accept a single shared credential.
Recorded in `unresolved-items.md` §2.

---

## 3. Call-site table

Surface legend: `API` = request/response path, `TASK` = Celery task,
`CMD` = management command, `PLUGIN` = plugin-owned.

| # | File | Line | Symbol | Operation | Bucket | Surface | Exposes direct object-storage URL | Full read into memory | Replaceable by Django Storage API |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `care/emr/utils/file_manager.py` | 35-50 | `S3FilesManager.signed_url` | `generate_presigned_url("put_object")` | per instance | API | **yes** | no | **no** — see §4.1 |
| 2 | `care/emr/utils/file_manager.py` | 52-69 | `S3FilesManager.read_signed_url` | `generate_presigned_url("get_object")` | per instance | API | **yes** | no | **no** — see §4.1 |
| 3 | `care/emr/utils/file_manager.py` | 71-79 | `S3FilesManager.put_object` | `put_object` | per instance | API + TASK | no | caller-dependent | **yes** — `Storage.save()` |
| 4 | `care/emr/utils/file_manager.py` | 81-88 | `S3FilesManager.get_object` | `get_object` | per instance | TASK + test | no | no (returns stream) | **yes** — `Storage.open()` |
| 5 | `care/emr/utils/file_manager.py` | 90-94 | `S3FilesManager.file_contents` | `get_object` + `Body.read()` | per instance | inferred: none | no | **yes** — `.read()` line 93 | **yes** — `Storage.open().read()` |
| 6 | `care/emr/utils/file_manager.py` | 96-110 | `S3FilesManager.delete_object` | `delete_object` | per instance | TASK | no | no | **yes** — `Storage.delete()` |
| 7 | `care/emr/utils/file_manager.py` | 112-133 | `S3FilesManager.delete_objects` | `delete_objects` (batch) | per instance | inferred: none | no | no | **partial** — see §4.2 |
| 8 | `care/utils/file_uploads/cover_image.py` | 14-21 | `delete_cover_image` | `delete_object` | `FACILITY` | API | no | no | **yes** |
| 9 | `care/utils/file_uploads/cover_image.py` | 24-53 | `upload_cover_image` | `delete_object` (line 35) + `put_object` (line 51) | `FACILITY` | API | no | no | **partial** — ACL, see §4.3 |
| 10 | `care/emr/models/file_upload.py` | 33 | `FileUpload.files_manager` | class attribute binding | `PATIENT` | — | — | — | n/a |
| 11 | `care/emr/models/report/report_upload.py` | 34 | `ReportUpload.files_manager` | class attribute binding | `REPORT` | — | — | — | n/a |
| 12 | `care/emr/api/viewsets/file_upload.py` | 262 | `FileUploadViewSet.upload_file` | `put_object` | `PATIENT` | API | no | **yes** — see §5.2 | **yes** |
| 13 | `care/emr/resources/file_upload/spec.py` | 115 | `FileUploadRetrieveSpec.perform_extra_serialization` | `signed_url` | `PATIENT` | API | **yes** | no | **no** |
| 14 | `care/emr/resources/file_upload/spec.py` | 117 | `FileUploadRetrieveSpec.perform_extra_serialization` | `read_signed_url` | `PATIENT` | API | **yes** | no | **no** |
| 15 | `care/emr/resources/report/report_upload/spec.py` | 52 | `ReportUploadRetrieveSpec.perform_extra_serialization` | `signed_url` | `REPORT` | API | **yes** | no | **no** |
| 16 | `care/emr/resources/report/report_upload/spec.py` | 54 | `ReportUploadRetrieveSpec.perform_extra_serialization` | `read_signed_url` | `REPORT` | API | **yes** | no | **no** |
| 17 | `care/emr/reports/report_utils.py` | 124-126 | `generate_and_upload_report` | `put_object` | `REPORT` | TASK | no | **yes** — `output_bytes` | **yes** |
| 18 | `care/emr/tasks/cleanup_incomplete_file_uploads.py` | 33 | `cleanup_incomplete_file_uploads` | `delete_object` | `PATIENT` | TASK | no | no | **yes** |
| 19 | `care/emr/reports/context_builder/data_points/fileupload.py` | 29 | data-point `mapping` lambda | `read_signed_url` | `PATIENT` | TASK | **yes** | no | **no** |

### 3.1 Test-only call sites (not counted above)

**verified** — listed for completeness, excluded from the 19:

| File | Line | Symbol |
| --- | --- | --- |
| `care/emr/tests/test_file_upload_api.py` | 19 | `@override_settings(FILE_UPLOAD_BUCKET_EXTERNAL_ENDPOINT=settings.BUCKET_ENDPOINT)` |
| `care/emr/tests/test_file_upload_api.py` | 77, 102, 137, 165 | asserts on `signed_url` / `read_signed_url` response fields |
| `care/emr/tests/test_file_upload_api.py` | 180 | `file_obj.files_manager.get_object(file_obj)` |

---

## 4. Call sites that block a straight Django Storage swap

### 4.1 Presigned URL generation (call sites 1, 2, 13-16, 19)

**verified** `signed_url` and `read_signed_url` call
`boto3.client("s3").generate_presigned_url(...)`
(`file_manager.py:46` and `file_manager.py:61`).

**verified** Django's `Storage` API has no presigned-URL method. `Storage.url()`
exists but its semantics are backend-defined, and `django-storages` implements
GCS signing through `GoogleCloudStorage.url()` rather than through a portable API.

**verified** `signed_url` is a **write** URL — `generate_presigned_url("put_object", ...)`
at `file_manager.py:46-47`. This is the direct browser-to-bucket upload path that
the stated architecture goal excludes.

**verified** `read_signed_url` sets `ResponseContentDisposition`
(`file_manager.py:66`) computed from a MIME allowlist `SAFE_INLINE_FORMATS`
(`file_manager.py:11-20`). Any Django-proxied download must reproduce this
`inline` vs `attachment` decision (`file_manager.py:57-59`) or it changes browser
behavior for patient documents.

### 4.2 Batch delete (call site 7)

**verified** `delete_objects` (`file_manager.py:112-133`) already contains a
GCP-specific branch:

```python
# care/emr/utils/file_manager.py:128-133
except ClientError as e:
    if e.response["Error"]["Code"] == "NotImplemented":
        # bulk delete is not supported by some providers: GCP
        msg = f"Batch delete objects not implemented for {self.bucket_type.value} bucket"
        raise NotImplementedError(msg) from e
    raise
```

**verified** This comment at `file_manager.py:130` is one of only two pre-existing
GCP references in application code (the other is the `CSProvider.GCP` enum member
at `care/utils/csp/config.py:20`).

**verified** No caller of `delete_objects` exists in this repository. A grep for
`delete_objects` returns only its definition (`file_manager.py:112`, `:123`) and
the prompt document. It is dead code as of this commit.

### 4.3 ACL on cover-image upload (call site 9)

**verified** `care/utils/file_uploads/cover_image.py:49-51`:

```python
if settings.BUCKET_HAS_FINE_ACL:
    boto_params["ACL"] = "public-read"
s3.put_object(**boto_params)
```

**verified** `BUCKET_HAS_FINE_ACL` is defined at `config/settings/base.py:531`
and read at exactly one place: `cover_image.py:49`.

**inferred** GCS buckets with uniform bucket-level access reject per-object ACLs.
`django-storages` `GoogleCloudStorage` does not expose a per-object ACL parameter
in the same shape. This branch needs an explicit decision, not a mechanical port.

---

## 5. Files read fully into memory

**verified** Three call sites materialize whole file bodies:

| Site | File | Line | What is buffered |
| --- | --- | --- | --- |
| 5 | `care/emr/utils/file_manager.py` | 93 | `response["Body"].read()` — entire object |
| 12 | `care/emr/api/viewsets/file_upload.py` | 224, 229 | base64-decoded request body |
| 17 | `care/emr/reports/report_utils.py` | 96, 124 | rendered report `output_bytes` |

### 5.2 The `upload-file` endpoint already proxies through Django

**verified** `FileUploadViewSet.upload_file`
(`care/emr/api/viewsets/file_upload.py:213-270`, route `POST /api/v1/files/upload-file/`)
accepts a **base64 string** in the JSON field `file_data`
(`file_upload.py:216`), decodes it (`file_upload.py:224`), wraps it in a
`ContentFile` (`file_upload.py:229`) and calls `put_object`
(`file_upload.py:262`).

**verified** This means a Django-proxied upload path **already exists** and is
routed. It is not a greenfield addition.

**verified** Constraints on that existing path:

- `file_upload.py:224` — `base64.b64decode(file_data)` holds the whole file in
  memory; base64 inflates the transferred body by ~33%.
- `file_upload.py:231-234` — size ceiling is `settings.MAX_FILE_UPLOAD_SIZE` MB,
  defined at `config/settings/config.py:22` with a default of **5 MB**.
- `file_upload.py:237` — MIME sniffed from the first 2048 bytes via `magic.from_buffer`.
- `file_upload.py:242-244` — MIME checked against `settings.ALLOWED_MIME_TYPES`.
- `file_upload.py:255-268` — the DB row and the `put_object` share one
  `transaction.atomic()` block. The storage write is **not** transactional; a
  commit failure after a successful `put_object` orphans the object. See
  `unresolved-items.md` §5.

**inferred** For Cloud Run, the base64 body plus the in-memory decode sets the
per-request memory floor at roughly 2× file size. Cloud Run's 32 MiB default
request limit for HTTP/1 also caps effective upload size below
`MAX_FILE_UPLOAD_SIZE` unless HTTP/2 is used. Not verified against a deployed
service.

---

## 6. Direct (unsigned) object-storage URLs

**verified** Two call sites build bucket URLs by string concatenation, outside
`S3FilesManager` entirely:

| File | Line | Symbol |
| --- | --- | --- |
| `care/facility/models/facility.py` | 211 | `Facility.read_cover_image_url` |
| `care/users/models.py` | 206 | `User.read_profile_picture_url` |

```python
# care/facility/models/facility.py:207-212
def read_cover_image_url(self):
    if self.cover_image_url:
        if settings.FACILITY_CDN:
            return f"{settings.FACILITY_CDN}/{self.cover_image_url}"
        return f"{settings.FACILITY_S3_BUCKET_EXTERNAL_ENDPOINT}/{settings.FACILITY_S3_BUCKET}/{self.cover_image_url}"
    return None
```

**verified** `care/users/models.py:202-207` is the same construction against the
same two settings.

**verified** These URLs are unsigned and depend on the object being publicly
readable — which is what `BUCKET_HAS_FINE_ACL` / `ACL: public-read`
(`cover_image.py:49-51`) provides.

**inferred** Facility cover images and user avatars are therefore *public* objects,
unlike patient files which are always signed. A GCP design that makes the bucket
uniformly private breaks both methods unless a Django-served route replaces them.

---

## 7. Settings inventory

**verified** All bucket settings, `config/settings/base.py`:

| Setting | Line | Default | Read by |
| --- | --- | --- | --- |
| `BUCKET_PROVIDER` | 525 | `"aws"`, uppercased | `csp/config.py:35, 48, 62` |
| `BUCKET_REGION` | 526 | `"ap-south-1"` | defaults only |
| `BUCKET_KEY` | 527 | `""` | defaults only |
| `BUCKET_SECRET` | 528 | `""` | defaults only |
| `BUCKET_ENDPOINT` | 529 | `""` | defaults only |
| `BUCKET_EXTERNAL_ENDPOINT` | 530 | `BUCKET_ENDPOINT` | defaults only |
| `BUCKET_HAS_FINE_ACL` | 531 | `False` | `cover_image.py:49` |
| `FILE_UPLOAD_BUCKET` | 536 | `""` | `csp/config.py:56, 70` |
| `FILE_UPLOAD_REGION` | 537 | `BUCKET_REGION` | **nothing** |
| `FILE_UPLOAD_KEY` | 538 | `BUCKET_KEY` | **nothing** |
| `FILE_UPLOAD_SECRET` | 539 | `BUCKET_SECRET` | **nothing** |
| `FILE_UPLOAD_BUCKET_ENDPOINT` | 540-542 | `BUCKET_ENDPOINT` | `csp/config.py:54, 68` |
| `FILE_UPLOAD_BUCKET_EXTERNAL_ENDPOINT` | 543-547 | conditional | `csp/config.py:52, 66` |
| `FACILITY_S3_BUCKET` | 660 | `""` | `csp/config.py:43`; `facility.py:211`; `users/models.py:206` |
| `FACILITY_S3_REGION` | 661 | `BUCKET_REGION` | `csp/config.py:34, 47, 61` |
| `FACILITY_S3_KEY` | 662 | `BUCKET_KEY` | `csp/config.py:36, 49, 63` |
| `FACILITY_S3_SECRET` | 663 | `BUCKET_SECRET` | `csp/config.py:37, 50, 64` |
| `FACILITY_S3_BUCKET_ENDPOINT` | 664-666 | `BUCKET_ENDPOINT` | `csp/config.py:41` |
| `FACILITY_S3_BUCKET_EXTERNAL_ENDPOINT` | 667-671 | conditional | `csp/config.py:39`; `facility.py:211`; `users/models.py:206` |

**verified** `BUCKET_PROVIDER` is validated against `CSProvider.__members__` at
`base.py:533-534`, but an invalid value only logs an error — it does not raise.

**verified** `CSProvider` (`csp/config.py:17-24`) already includes a `GCP` member
at line 20. **verified** `BUCKET_PROVIDER` is only ever compared against
`CSProvider.AWS_ROLE_BASED` (`csp/config.py:35, 48, 62`); the `GCP` member is
never branched on anywhere in the repository.

---

## 8. Replaceability assessment

| Category | Call sites | Django Storage API verdict |
| --- | --- | --- |
| Plain read/write/delete | 3, 4, 5, 6, 8, 12, 17, 18 | **Replaceable.** `save()` / `open()` / `delete()` cover these. |
| Batch delete | 7 | Dead code; delete it or loop `Storage.delete()`. |
| ACL-tagged write | 9 | Needs a decision on public objects under GCS. |
| Presigned URL generation | 1, 2, 13-16, 19 | **Not replaceable.** Must become Django-served routes to meet the stated goal. |
| Unsigned URL construction | `facility.py:211`, `users/models.py:206` | **Not replaceable** as-is; depends on public objects. |

**inferred** 8 of 19 call sites port mechanically. The remaining 11 are the actual
migration work, and 9 of those exist only to hand object-storage URLs to the
browser — which the target architecture forbids.

---

## 11. IS-01 migration status

Recorded 2026-08-06 on `feature/django-storages`. The prediction in §8 held: the
8 mechanical sites migrated, the 2 dead ones were deleted, and the 9 URL-handing
sites remain for IS-02.

### 11.1 Status of every call site

Numbering follows the §3 table.

Final status, after the ES-01 completion pass removed the signed-URL transport.

| # | Symbol | Status |
| --- | --- | --- |
| 1 | `signed_url` | **removed** — presigned PUT deleted; uploads use the Django endpoint |
| 2 | `read_signed_url` | **removed** — replaced by `GET /files/{id}/download/` |
| 3 | `put_object` | `migrated_to_django_storage` — `Storage.save()` |
| 4 | `get_object` | `migrated_to_django_storage` — `Storage.open()` |
| 5 | `file_contents` | `migrated_to_django_storage` — `Storage.open().read()`; still no caller |
| 6 | `delete_object` | `migrated_to_django_storage` — `Storage.delete()` |
| 7 | `delete_objects` | **removed** — dead code, and no portable batch delete exists |
| 8 | `delete_cover_image` | `migrated_to_django_storage` — `storages["facility"].delete()` |
| 9 | `upload_cover_image` | `migrated_to_django_storage` — `storages["facility"].save()`, no ACL |
| 10 | `FileUpload.files_manager` | `temporary_wrapper` — `FilesManager("patient")` |
| 11 | `ReportUpload.files_manager` | `temporary_wrapper` — `FilesManager("report")` |
| 12 | `FileUploadViewSet.upload_file` | `migrated_to_django_storage` — persistence *and* transport; multipart since ES-02 |
| 13-16 | signed/read URL fields on both retrieve specs | **removed** — replaced by `download_url`, a CARE route |
| 17 | `generate_and_upload_report` | `migrated_to_django_storage` — `Storage.save()` with `ContentFile` |
| 18 | `cleanup_incomplete_file_uploads` | `migrated_to_django_storage` — `Storage.delete()` |
| 19 | report data point `read_signed_url` | **removed** — embeds a CARE download route instead |
| — | `facility.py`, `users/models.py` URL builders | `migrated_to_django_storage` — now reverse to CARE asset routes |

Totals: **11 migrated**, **2 temporary wrapper** (the two `files_manager`
bindings), **6 removed**.

Nothing is `legacy_signed_url_only`. Nothing is `blocked`.

### 11.1a Transport now mediated by CARE

| Route | Serves | Auth |
| --- | --- | --- |
| `GET /api/v1/files/{external_id}/download/` | patient files | `file_authorizer` via `get_queryset` |
| `GET /api/v1/template_reports/{external_id}/download/` | reports | `read_report_authorizer`, called explicitly |
| `GET /api/v1/assets/facility/{external_id}/cover_image/` | cover images | anonymous |
| `GET /api/v1/assets/user/{username}/profile_picture/` | avatars | anonymous |

**verified** The two asset routes are anonymous by design. `AllFacilityViewSet`
and `FacilitySchedulableUsersViewSet` are unauthenticated and already expose
these images, so who can see them is unchanged. What changed is that CARE reads
the bytes through Django Storage, which lets the bucket be private. They are
separate views because `FacilityViewSet` and `UserViewSet` filter their
querysets by `request.user` and cannot serve an anonymous request.

**verified** All four stream via `FileResponse`; nothing buffers a whole object
to serve it. The inline-vs-attachment decision that presigned
`ResponseContentDisposition` used to make is preserved in
`care/emr/utils/file_download.py`.

### 11.2 Architecture now in place

**verified** Application code addresses logical aliases; the provider is chosen
in settings alone.

| Alias | Physical bucket setting | Consumers |
| --- | --- | --- |
| `patient` | `CARE_PATIENT_STORAGE_BUCKET` (defaults to `FILE_UPLOAD_BUCKET`) | `FileUpload.files_manager` |
| `facility` | `CARE_FACILITY_STORAGE_BUCKET` (defaults to `FACILITY_S3_BUCKET`) | `care/utils/file_uploads/cover_image.py` |
| `report` | `CARE_REPORT_STORAGE_BUCKET` (defaults to `FILE_UPLOAD_BUCKET`) | `ReportUpload.files_manager` |
| `staticfiles` | — | WhiteNoise, unchanged |

**verified** `CARE_STORAGE_BACKEND` selects `s3` (default) or `gcs`. An
unsupported value raises `ImproperlyConfigured` naming the supported values.

**verified** `report` and `patient` still resolve to the same physical bucket, as
before, but are independently configurable.

### 11.3 Object-name generation

**verified** `care/emr/utils/file_manager.py:get_storage_name` is the single
provider-neutral name helper. The `<file_type>/<internal_name>` convention is
preserved byte-for-byte; names are relative and carry no bucket, URL or endpoint.
Traversal, absolute paths and empty components raise `SuspiciousFileOperation`.

**verified** Cover images and avatars keep their own unrelated convention,
`<folder>/<external_id>_<token>.<ext>`, and are addressed through the alias
directly rather than through `FilesManager`.

### 11.3a One source of truth per logical bucket

**verified** Each logical bucket is resolved in exactly one place — the
`STORAGES` alias built in `config/settings/base.py`. Nothing else derives a
bucket name.

| Alias | Setting | Fallback |
| --- | --- | --- |
| `patient` | `CARE_PATIENT_STORAGE_BUCKET` | `FILE_UPLOAD_BUCKET` |
| `facility` | `CARE_FACILITY_STORAGE_BUCKET` | `FACILITY_S3_BUCKET` |
| `report` | `CARE_REPORT_STORAGE_BUCKET` | `FILE_UPLOAD_BUCKET` |

**This closes a defect introduced earlier in IS-01.** While the signed-URL path
survived, it resolved buckets through `care/utils/csp/`, which read the *old*
settings. Setting `CARE_PATIENT_STORAGE_BUCKET` therefore moved persistence but
not the URLs, so uploads and downloads silently addressed different buckets —
on the default `s3` profile, not only under `gcs`. Removing the signed-URL
transport removes the second resolver, so the divergence is now structurally
impossible: `download_url` names a CARE route and carries no bucket at all.

### 11.4 §2.1 credential defect — corrected

**verified** The defect recorded in §2.1 is fixed. The `patient` and `report`
aliases now read `FILE_UPLOAD_REGION`, `FILE_UPLOAD_KEY` and
`FILE_UPLOAD_SECRET`; `facility` reads the `FACILITY_S3_*` set. The three
`FILE_UPLOAD_*` credential settings listed as dead in §7 are now live.

**Behaviour change.** Locally every one of these resolves to the same MinIO
value, so there is no local change. A deployment that sets `FACILITY_S3_KEY` to
something other than `BUCKET_KEY` *without* also setting `FILE_UPLOAD_KEY` will
now use `BUCKET_KEY` for patient and report objects and must set
`FILE_UPLOAD_KEY` explicitly.

**verified** `get_patient_bucket_config` and `get_report_bucket_config` in
`care/utils/csp/config.py` still contain the original defect. They are now
reached only by the legacy signed-URL path, which is why they were left alone;
IS-02 removes them.

### 11.5 Provider SDK use remaining

**verified** After the ES-01 completion pass, **no storage module imports a
provider SDK**. `boto3` / `botocore` appear in exactly two non-test modules, and
neither performs object storage:

| File | Line | Use | Why retained |
| --- | --- | --- | --- |
| `care/emr/tasks/report_generation.py` | 1 | `ClientError` in `autoretry_for` | Retry configuration only; never instantiates a client. Under `s3` django-storages raises it from inside `Storage.save`, so retry is unchanged; under `gcs` it would not fire. Left alone because the completion pass forbids modifying Celery. See §11.7 |
| `care/utils/sms/backend/sns.py` | 8-9, 44, 55 | SNS client | SMS delivery, not storage |

**verified** No module imports `google.cloud.storage` directly. GCS is reached
only through `django-storages`.

**verified** `care/utils/csp/` is deleted. `BucketType`, `CSProvider`,
`ClientConfig` and `get_client_config` existed only to resolve provider
credentials and external endpoints for signed URLs, and have no consumer left.
`BUCKET_PROVIDER` survives as the credential-source switch, compared against a
literal in `config/storage.py`.

**verified** Settings deleted for want of a consumer: `FACILITY_CDN`,
`BUCKET_HAS_FINE_ACL`, `BUCKET_EXTERNAL_ENDPOINT`,
`FILE_UPLOAD_BUCKET_EXTERNAL_ENDPOINT`, `FACILITY_S3_BUCKET_EXTERNAL_ENDPOINT`.

### 11.6 Whole-file reads remaining

Updated from §5.

| Site | File | Status |
| --- | --- | --- |
| 5 | `file_manager.file_contents` | Retained as an explicit opt-in; still no production caller. `get_object` returns a stream and is the default. |
| 12 | `file_upload.py` base64 decode | **Gone (ES-02).** Multipart replaced it. Django's upload handlers decide memory vs temporary file; CARE reads only the leading 2048 bytes to sniff the MIME type and hands the `UploadedFile` straight to `Storage.save()`. |
| 17 | `report_utils.py` `output_bytes` | **Remains.** The renderer returns complete bytes; ES-01 §18 explicitly does not require redesigning report generation. |

**verified** `upload_cover_image` no longer buffers: the `UploadedFile` is passed
to `Storage.save()` directly instead of `image.file` being handed to
`put_object`.

### 11.7 Known gap — retry under the GCS profile

**verified** `care/emr/tasks/report_generation.py:13` retries on
`botocore.exceptions.ClientError`. Under `CARE_STORAGE_BACKEND=gcs`, storage
failures raise `google.api_core.exceptions.*`, so report generation would not
retry. Generation itself still succeeds; only the retry-on-transient-failure
behaviour is absent.

**Not changed.** Both ES-01 §31 and the completion pass forbid modifying Celery.
This is the last provider-specific reference in a storage consumer and is the
one item that should be resolved before the GCS profile is used in anger.
Recorded in `unresolved-items.md` S2.

### 11.8 Remaining compatibility layers

**verified** Two, both deliberate:

| Layer | Purpose | Removal |
| --- | --- | --- |
| `FilesManager` | Binds `FileUpload` / `ReportUpload` to a logical alias. Pure Django Storage; no provider import or branch. | Optional. It is a convenience, not a portability risk. |
| `S3FilesManager` | Deprecated subclass kept so external plugins that import the old name keep working. Warns, delegates to Django Storage, exposes **no** signed-URL method, rejects unknown aliases. | After plugin authors migrate; see `plugin-impact.md`. |

**verified** The base64 upload transport at `POST /api/v1/files/upload-file/` was
removed by ES-02 and replaced with `multipart/form-data`. No upload path buffers
a complete file any more. See `frontend-file-flow.md` §12.
