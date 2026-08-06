---
title: Storage Call-Site Inventory
document: inventory/storage-call-sites
version: 0.1.0
status: Draft
phase: 0
source_repository: https://github.com/ohcnetwork/care
source_branch: gcp
source_commit: 6a2976dc2512c2c532fcc70628c5690fbbbe3f3d
reviewed: 2026-08-05
---

# Storage Call-Site Inventory

Every object-storage call site in the repository, enumerated. No storage code was
modified in this phase.

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
