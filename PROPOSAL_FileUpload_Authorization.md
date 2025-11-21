## Proposal: Secure Diagnostic & Service Request File Uploads

### Summary
- **Issue**: `FileUploadViewSet` skipped authorization when handling `diagnostic_report` and `service_request` files (`care/care/emr/api/viewsets/file_upload.py`, former TODO at line ~76).
- **Risk**: Unauthorized clinicians could read or upload sensitive diagnostic attachments, violating facility data-sharing rules and privacy policies.
- **Resolution**: Enforce read/write checks using the existing `AuthorizationController` hooks for `ServiceRequest` and `DiagnosticReport` resources.

### Technical Scope
- **Files Updated**
  - `care/care/emr/api/viewsets/file_upload.py`
  - `care/care/emr/tests/test_file_upload_api.py`
- **Key Logic**
  - Service request files now call `can_read_service_request` / `can_write_service_request`.
  - Diagnostic report files resolve their parent `ServiceRequest` and call `can_read_diagnostic_report` / `can_write_diagnostic_report`.
  - Permission failures raise `PermissionDenied`, blocking both upload and retrieval paths.
- **Imports Added**
  - `DiagnosticReport` and `ServiceRequest` models, plus new test fixtures (`patch`, `baker`, `FileTypeChoices`).

### Testing
- Added four regression tests (`care/care/emr/tests/test_file_upload_api.py`):
  1. Service-request upload denied without `can_write_service_request`.
  2. Diagnostic-report upload denied without `can_write_diagnostic_report`.
  3. Service-request download denied without `can_read_service_request`.
  4. Diagnostic-report download denied without `can_read_diagnostic_report`.
- Tests patch `AuthorizationController.call` to simulate permission outcomes and verify the correct hooks fire.
- **Note**: Automated test run was attempted (`pipenv run python manage.py test care.emr.tests.test_file_upload_api`) but `pipenv` is unavailable in the current environment. Please run the suite locally once `pipenv` is installed.

### Impact & Value
1. **Security**: Closes a direct path to improperly access diagnostic attachments.
2. **Compliance**: Aligns file handling with existing encounter/patient access patterns.
3. **Clarity**: Removes lingering TODO, codifies the expected authorization workflow.
4. **Regression Coverage**: New tests ensure future refactors cannot silently reintroduce the gap.

### Difficulty
- **Level**: Intermediate
- Requires understanding DRF viewsets, Care’s authorization facade, and the relationship between `DiagnosticReport` and `ServiceRequest`.

### Next Steps / Follow-ups
- Run the refreshed test suite once `pipenv` (or the project’s preferred virtualenv) is available.
- Optionally extend coverage to other file categories if similar authorization gaps surface.

