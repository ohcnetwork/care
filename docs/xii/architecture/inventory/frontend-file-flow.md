---
title: Frontend File-Flow Inventory
document: inventory/frontend-file-flow
version: 0.1.0
status: Draft
phase: 0
source_repository: https://github.com/ohcnetwork/care
source_branch: gcp
source_commit: 6a2976dc2512c2c532fcc70628c5690fbbbe3f3d
reviewed: 2026-08-05
---

# Frontend File-Flow Inventory

The file-related API contract as it exists today, and the exact changes required
to route all file traffic through Django. No API was modified in this phase.

Evidence labels: **verified** / **inferred** / **unknown**.

**Scope note:** this repository is the Django backend only. The CARE frontend
lives in a separate repository. Everything below is derived from the backend's
routes, serializers and tests. Frontend behavior is **inferred** from the response
contract, never observed.

---

## 1. Routes

**verified** `config/api_router.py`:

| Line | Registration | Base path |
| --- | --- | --- |
| 122 | `router.register("files", FileUploadViewSet, basename="files")` | `/api/v1/files/` |
| 500 | `router.register("template_reports", ReportUploadViewSet, basename="template-reports")` | `/api/v1/template_reports/` |

**verified** `FileUploadViewSet` (`care/emr/api/viewsets/file_upload.py:119-121`)
mixes in `EMRCreateMixin`, `EMRRetrieveMixin`, `EMRUpdateMixin`, `EMRListMixin`.
There is **no destroy mixin** — files are archived, not deleted.

---

## 2. Current upload flow — two paths coexist

### 2.1 Path A: presigned PUT (the default)

**verified** Three steps:

| Step | Endpoint | Handler | What the client gets |
| --- | --- | --- | --- |
| 1. Initiate | `POST /api/v1/files/` | `EMRCreateMixin` → `FileUploadCreateSpec` | `FileUploadRetrieveSpec` including **`signed_url`** |
| 2. Upload | **direct to object storage** | none — browser PUTs to the bucket | — |
| 3. Complete | `POST /api/v1/files/{external_id}/mark_upload_completed/` | `file_upload.py:177-184` | `FileUploadListSpec` |

**verified** Step 1 returns a write URL because
`FileUploadCreateSpec.perform_extra_deserialization` sets
`obj._just_created = True` (`care/emr/resources/file_upload/spec.py:51`), and
`FileUploadRetrieveSpec.perform_extra_serialization` branches on that flag:

```python
# care/emr/resources/file_upload/spec.py:110-117
@classmethod
def perform_extra_serialization(cls, mapping, obj):
    super().perform_extra_serialization(mapping, obj)
    if getattr(obj, "_just_created", False):
        # Calculate Write URL and return it
        mapping["signed_url"] = obj.files_manager.signed_url(obj)   # line 115
    else:
        mapping["read_signed_url"] = obj.files_manager.read_signed_url(obj)  # line 117
```

**verified** `signed_url` is a presigned **`put_object`** URL
(`care/emr/utils/file_manager.py:46-47`) with a 3600 s default expiry
(`file_manager.py:35`).

**verified** Step 3 sets `upload_completed = True` (`file_upload.py:181`). This
matters because `get_queryset` filters list results on `upload_completed=True`
(`file_upload.py:169`) — a file never marked complete is invisible to listing.

**verified** Nothing verifies that an object actually exists in the bucket before
`mark_upload_completed` flips the flag. The endpoint trusts the client.

### 2.2 Path B: base64 through Django (already exists)

**verified** `POST /api/v1/files/upload-file/`
(`care/emr/api/viewsets/file_upload.py:213-270`, `url_path="upload-file"`).

**verified** Request body fields, read at `file_upload.py:215-216, 246-253`:

```
original_name      (required)   file_upload.py:215
file_data          (required)   base64 string, file_upload.py:216
name                            file_upload.py:248
associating_id                  file_upload.py:249
file_type                       file_upload.py:250
file_category                   file_upload.py:251
```

**verified** `mime_type` is **not** taken from the client — it is sniffed server
side with `magic.from_buffer(file_content[:2048], mime=True)`
(`file_upload.py:237`) and checked against `settings.ALLOWED_MIME_TYPES`
(`file_upload.py:242-244`).

**verified** Response is `FileUploadRetrieveSpec` (`file_upload.py:270`). Because
`file_upload.py:257` sets `_just_created = False`, the response contains
**`read_signed_url`**, not `signed_url` — so even this Django-proxied upload
hands back a direct object-storage read URL.

**verified** This path already satisfies "uploads pass through Django". It does
**not** satisfy "downloads pass through Django".

**verified** No `mark_upload_completed` call is needed — `file_upload.py:263`
sets the flag inline.

---

## 3. Current download flow

**verified** There is **no download endpoint**. Downloads happen entirely against
object storage.

| Response field | Produced at | Content |
| --- | --- | --- |
| `read_signed_url` | `care/emr/resources/file_upload/spec.py:117` | presigned `get_object` URL |
| `read_signed_url` | `care/emr/resources/report/report_upload/spec.py:54` | presigned `get_object` URL |

**verified** `read_signed_url` (`care/emr/utils/file_manager.py:52-69`) sets
`ResponseContentDisposition` (`:66`) using a MIME allowlist:

```python
# care/emr/utils/file_manager.py:11-20, 56-59
SAFE_INLINE_FORMATS = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "image/tiff", "image/bmp", "image/x-icon", "application/pdf",
}
...
mime_type = file_obj.meta.get("mime_type")
content_disposition = "inline" if mime_type in SAFE_INLINE_FORMATS else "attachment"
```

**inferred** The frontend renders images and PDFs inline and downloads everything
else, relying on the storage provider to honor `ResponseContentDisposition`. Any
Django-served replacement must set the same `Content-Disposition` header or the
browser behavior changes for every non-image attachment.

**verified** Expiry is 3600 s (`file_manager.py:52`).

---

## 4. Unsigned public URLs — cover images and avatars

**verified** A third file flow exists that uses neither presigned URLs nor
`S3FilesManager`.

| Endpoint | Handler | Line |
| --- | --- | --- |
| `POST/DELETE /api/v1/facility/{external_id}/cover_image/` | `FacilityViewSet.cover_image` | `care/emr/api/viewsets/facility.py:119-121` |
| user profile picture | `care/emr/api/viewsets/user.py:43-48` | serializer fields |

**verified** These accept a **multipart `ImageField`**
(`facility.py:39-42`, `user.py:43-46`) — a genuine file upload through Django,
not base64, not presigned. The action is explicitly bound to `MultiPartParser`
at `facility.py:119` via
`@method_decorator(parser_classes([MultiPartParser]))`.

**inferred** This is the closest existing precedent in the codebase for the
streaming multipart upload that change U2 (§9.1) requires — worth reusing rather
than designing fresh.

**verified** Response fields are `read_cover_image_url`
(`facility.py:44`) and `read_profile_picture_url` (`user.py:48`), both
`serializers.URLField(read_only=True)`.

**verified** Those URLs are built by string concatenation against the bucket:

```python
# care/facility/models/facility.py:207-212
def read_cover_image_url(self):
    if self.cover_image_url:
        if settings.FACILITY_CDN:
            return f"{settings.FACILITY_CDN}/{self.cover_image_url}"
        return f"{settings.FACILITY_S3_BUCKET_EXTERNAL_ENDPOINT}/{settings.FACILITY_S3_BUCKET}/{self.cover_image_url}"
    return None
```

**verified** `care/users/models.py:202-207` is identical in shape.

**verified** These objects are written with `ACL: public-read` when
`settings.BUCKET_HAS_FINE_ACL` is true (`care/utils/file_uploads/cover_image.py:49-51`).

**inferred** Cover images and avatars are therefore **public, unauthenticated
objects**. Unlike patient files, no signature gates them. A GCS bucket with
uniform bucket-level access breaks both the write (ACL rejected) and the read
(object not public).

---

## 5. Serializers and response contract

**verified** Pydantic specs, not DRF serializers, for files and reports:

| Spec | File | Fields carrying storage URLs |
| --- | --- | --- |
| `FileUploadRetrieveSpec` | `care/emr/resources/file_upload/spec.py:105-117` | `signed_url` (`:106`), `read_signed_url` (`:107`) |
| `FileUploadListSpec` | `care/emr/resources/file_upload/spec.py:76-102` | **none** |
| `ReportUploadRetrieveSpec` | `care/emr/resources/report/report_upload/spec.py:43-54` | `signed_url` (`:44`), `read_signed_url` (`:45`) |
| `ReportUploadListSpec` | `care/emr/resources/report/report_upload/spec.py:19-40` | **none** |

**verified** Both URL fields are `str | None = None` — optional and mutually
exclusive in practice, because the `_just_created` branch sets exactly one.

**verified** `FileUploadRetrieveSpec` also exposes `internal_name`
(`spec.py:108`), carrying an in-source comment:
`# Not sure if this needs to be returned`. `internal_name` is the storage object
key (`care/emr/models/file_upload.py:45-49`). **inferred** Leaking the object key
is low risk while the bucket is private, but it is unnecessary surface.

**verified** DRF serializers are used for the cover-image flow only
(`facility.py:39-49`, `user.py:43-48`).

---

## 6. OpenAPI schema

**verified** `drf-spectacular` is the schema generator (`Pipfile`,
`drf-spectacular = "==0.29.0"`).

**verified** Explicit schema annotations on the file endpoints:

| Endpoint | Annotation | Line |
| --- | --- | --- |
| `mark_upload_completed` | `@extend_schema(responses={200: FileUploadListSpec})` | `file_upload.py:176` |
| `archive` | `@extend_schema(request=ArchiveRequestSpec, responses={200: FileUploadListSpec})` | `file_upload.py:189-192` |
| report `archive` | `@extend_schema(request=ArchiveRequestSpec, responses={200: ReportUploadListSpec})` | `report/report_upload.py:162` |

**verified** `upload_file` at `file_upload.py:213` has **no** `@extend_schema`
decorator. Its request body — `original_name` and base64 `file_data` — is read
directly from `request.data` and is therefore **absent from the generated
OpenAPI schema**. Any client generated from the schema cannot discover this
endpoint's contract. Recorded in `unresolved-items.md` §9.

**verified** A dedicated locmem cache is reserved for schema generation:
`"swagger_cache"` at `config/settings/base.py:96-99`.

---

## 7. Tests covering the contract

**verified** `care/emr/tests/test_file_upload_api.py`:

| Line | What it asserts |
| --- | --- |
| 19 | `@override_settings(FILE_UPLOAD_BUCKET_EXTERNAL_ENDPOINT=settings.BUCKET_ENDPOINT)` on the test class |
| 77 | `response.data["signed_url"]` present on create |
| 102 | `response.data["read_signed_url"]` present on retrieve |
| 137 | `read_signed_url` present |
| 165 | `signed_url` present |
| 177 | `cleanup_incomplete_file_uploads.delay()` |
| 180 | `file_obj.files_manager.get_object(file_obj)` raises after cleanup |

**verified** The `@override_settings` at line 19 exists because signed URLs are
generated against the **external** endpoint while the test process reaches
storage on the **internal** one. This is the `external=True` branch in
`care/utils/csp/config.py:73` propagating into tests.

**verified** These tests assert on the **presence of the URL fields themselves**.
Removing `signed_url` / `read_signed_url` from the response breaks the suite at
lines 77, 102, 137 and 165 — the tests are coupled to the presigned-URL design,
not merely to file behavior.

**verified** The suite requires reachable object storage: line 180 performs a real
`get_object` and expects `ClientError` (imported at `test_file_upload_api.py:6`).

---

## 8. Frontend repository references

**verified** No frontend source exists in this repository.

**verified** Grep for `care_fe`, `ohcnetwork/care_fe` and similar across the
repository returns no code reference. The only cross-repository coupling found is
in CI: `.github/workflows/reusable-test.yml:98-109` uploads a database dump named
`care-db-dump` with the comment *"Upload dummy db as artifact so it can be used
to speed up frontend tests"*.

**unknown** Which frontend components consume `signed_url` / `read_signed_url`,
and whether any perform a direct browser PUT versus using the base64 endpoint.
This cannot be determined here. Recorded in `unresolved-items.md` §10.

**inferred** Because Path B (`upload-file`) exists and is routed, at least one
client is expected to use it. But since it is absent from the OpenAPI schema
(§6), it was likely added for a specific non-browser caller. Unconfirmed.

---

## 9. Exact API changes required to route all traffic through Django

The stated goal: all uploads and downloads pass through Django; no direct
browser-to-bucket transfer.

### 9.1 Upload

| # | Change | Location |
| --- | --- | --- |
| U1 | Stop returning `signed_url`. Remove the `_just_created` write branch. | `care/emr/resources/file_upload/spec.py:113-115`; `care/emr/resources/report/report_upload/spec.py:51-52` |
| U2 | Add a multipart upload endpoint that streams to storage rather than buffering base64. | new action on `FileUploadViewSet` |
| U3 | Decide the fate of the existing base64 endpoint — keep for compatibility or deprecate. | `care/emr/api/viewsets/file_upload.py:213-270` |
| U4 | Re-express `mark_upload_completed` as either server-set or a no-op retained for compatibility. | `care/emr/api/viewsets/file_upload.py:177-184` |
| U5 | Remove the presigned write method once no caller remains. | `care/emr/utils/file_manager.py:35-50` |

**verified** U1 is not cosmetic: `FileUploadRetrieveSpec` is the create response
(`file_upload.py:123-124` sets `pydantic_model` / `pydantic_retrieve_model`), so
removing the field changes the create contract.

### 9.2 Download

| # | Change | Location |
| --- | --- | --- |
| D1 | Add an authenticated download route, e.g. `GET /api/v1/files/{external_id}/download/`. | new action on `FileUploadViewSet` |
| D2 | Reproduce the `inline` vs `attachment` decision in a real `Content-Disposition` header. | port `care/emr/utils/file_manager.py:56-59, 66` |
| D3 | Stream the object rather than buffering. `file_contents` (`file_manager.py:90-94`) reads whole bodies. | `care/emr/utils/file_manager.py:90-94` |
| D4 | Apply `file_authorizer` on the download path. | reuse `care/emr/api/viewsets/file_upload.py:38-103` |
| D5 | Stop returning `read_signed_url`; return a Django URL instead. | `spec.py:117`; `report/report_upload/spec.py:54` |
| D6 | Same for the report data point used in report context. | `care/emr/reports/context_builder/data_points/fileupload.py:29` |

**verified** D4 is not automatic. `file_authorizer` currently runs in
`get_queryset` (`file_upload.py:157-173`) and in the create/update authorize
hooks. A new download action must call it explicitly, or it will serve any file
to any authenticated user.

**verified** D6 matters because
`care/emr/reports/context_builder/data_points/fileupload.py:29` embeds
`read_signed_url` into **generated report content**. A 1-hour signed URL baked
into a stored PDF expires; a Django URL does not. This is a behavior improvement,
but it changes what is rendered inside reports.

### 9.3 Cover images and avatars

| # | Change | Location |
| --- | --- | --- |
| C1 | Decide whether these objects stay public. | `care/utils/file_uploads/cover_image.py:49-51` |
| C2 | If private, replace both URL builders with Django routes. | `care/facility/models/facility.py:207-212`; `care/users/models.py:202-207` |
| C3 | Resolve the ACL call under uniform bucket-level access. | `care/utils/file_uploads/cover_image.py:49-51` |

### 9.4 Tests

| # | Change | Location |
| --- | --- | --- |
| T1 | Rewrite the four URL-presence assertions. | `care/emr/tests/test_file_upload_api.py:77, 102, 137, 165` |
| T2 | Reconsider the external-endpoint override, which exists only for presigned URLs. | `care/emr/tests/test_file_upload_api.py:19` |

### 9.5 Schema

| # | Change | Location |
| --- | --- | --- |
| S1 | Add `@extend_schema` to the upload endpoint so it appears in OpenAPI. | `care/emr/api/viewsets/file_upload.py:213` |
| S2 | Regenerate and diff the schema; `signed_url` / `read_signed_url` disappear from two response models. | — |

---

## 10. Summary of contract impact

**verified** Response fields removed or repurposed: **4**
(`signed_url` and `read_signed_url` on both `FileUploadRetrieveSpec` and
`ReportUploadRetrieveSpec`).

**verified** Endpoints added: **at least 2** (upload, download). Possibly 2 more
if cover images and avatars stop being public.

**verified** Endpoints whose meaning changes: **1**
(`mark_upload_completed`, `file_upload.py:177-184`).

**verified** Tests requiring rewrite: **4 assertions in 1 file**.

**inferred** The frontend must change in lockstep — this is a **breaking API
change**, not an additive one, unless both URL fields are retained as Django URLs
under their existing names. Retaining the names is the lower-risk path and would
let the backend migrate before the frontend, but it leaves the misleading
`signed_url` naming in place.
