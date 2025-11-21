# Report System API Documentation

## Overview
The report system allows generating customizable PDF/HTML reports from templates using patient/encounter data.

**Base URL**: `/api/v1`

---

## 1. Discovery & Schema Endpoints

### 1.1 Get Template Schema
**GET** `/template/schema/`
Get complete schema of available context builders and their fields for template building.

**Response**: Returns all available data sources (patient, encounter, allergies, medications, etc.) with their available fields.

---

### 1.2 Get Report Types
**GET** `/report/get_report_types/`
Get all available report types with their configurations.

**Response**:
```json
{
  "discharge_summary": {
    "display_name": "Discharge Summary",
    "description": "Discharge summary generated for an encounter",
    "associating_model": "Encounter"
  }
}
```

---

## 2. Template Management

### 2.1 List Templates
**GET** `/template/`
List all templates (facility-scoped or instance-level based on query params).

**Query Params**:
- `facility` (UUID) - Filter by facility
- `name` (string) - Search by name
- `template_type` - Filter by type (discharge_summary)
- `status` - Filter by status (draft/active/retired)

---

### 2.2 Create Template
**POST** `/template/`
Create a new report template.

```json
{
  "facility": "uuid-or-null",
  "slug_value": "my-discharge-template",
  "name": "Standard Discharge Summary",
  "status": "active",
  "template_type": "discharge_summary",
  "default_format": "pdf",
  "template_data": "<h1>Discharge Summary</h1><p>Patient: {{ patient.name }}</p>",
  "context_config": {
    "patient": {},
    "encounter": {},
    "medications": {
      "filters": {"status": "active"},
      "limit": 50
    }
  }
}
```

**Notes**:
- `facility`: null for instance-level, UUID for facility-scoped
- `slug_value`: Unique identifier (system adds prefix: `f-{facility_id}-{slug}` or `i-{slug}`)
- `status`: draft/active/retired (only "active" templates can generate reports)
- `default_format`: pdf/html (default output format for this template)
- `context_config`: Defines which data points to include and their query configuration
  - Single objects (patient, encounter): Must use empty dict `{}`
  - Querysets (medications, allergies, etc.): Can specify `filters` and/or `limit`
  - Fields are auto-detected from template_data, no need to list them

---

### 2.3 Retrieve Template
**GET** `/template/{slug}/`
Get template details by slug.

**Example**: `/template/i-my-discharge-template/` or `/template/f-{facility-uuid}-my-discharge-template/`

---

### 2.4 Update Template
**PATCH** `/template/{slug}/`
Update template metadata (name, status, etc.).

```json
{
  "name": "Updated Template Name",
  "status": "active"
}
```

**Note**: Currently does NOT support updating `template_data` or `context_config`.

---

### 2.5 Preview Template
**POST** `/template/preview/`
Preview a template with sample data before saving.

**✨ Auto-Detection**: Fields are automatically detected from template - no need to specify context_config!

```json
{
  "template_data": "<h1>{{ patient.name }}</h1><p>Age: {{ patient.age }}</p>",
  "output_format": "html",
  "options": {}
}
```

**Response**: Returns rendered HTML or PDF with validation results.

```json
{
  "html": "<h1>Ramesh Kumar</h1><p>Age: 45 years</p>",
  "validation": {
    "syntax_valid": true,
    "syntax_error": null,
    "render_valid": true,
    "render_error": null
  }
}
```

**Notes**:
- System automatically detects which data sources are used in the template
- All fields from detected builders are available in preview
- Invalid field references are caught during validation

---

## 3. Report Generation & Management

### 3.1 Generate Report
**POST** `/report/generate/`
Generate a report asynchronously from a template.

```json
{
  "template_id": "template-uuid",
  "report_type": "discharge_summary",
  "associating_id": "encounter-uuid",
  "encounter_id": "encounter-uuid",
  "patient_id": "patient-uuid",
  "context_config": null,
  "output_format": "pdf",
  "options": {
    "page_size": "A4",
    "margin": "10mm"
  }
}
```

**Fields**:
- `template_id`: UUID of the template to use
- `report_type`: Must match registered type (currently: "discharge_summary")
- `associating_id`: The primary resource ID (e.g., encounter UUID for discharge_summary)
- `encounter_id`, `patient_id`: Required by context builders (depends on what data the template needs)
- `context_config`: Override template's context_config (optional, uses template's if null)
- `output_format`: pdf/html
- `options`: PDF generation options (page_size, margins, etc.)

**Response**:
```json
{
  "detail": "Report generation started. You will receive a notification when complete."
}
```

**Note**: Report generation is asynchronous via Celery tasks.

---

### 3.2 List Reports
**GET** `/report/`
List generated reports.

**Query Params**:
- `name` - Search by name
- `template` - Filter by template slug
- `associating_id` - Filter by associating resource ID
- `is_archived` - Filter archived reports
- `upload_completed` - Filter completed reports
- `include_archived` - Include archived (default: false)

---

### 3.3 Retrieve Report
**GET** `/report/{id}/`
Get report details by UUID.

---

### 3.4 Download Report
**GET** `/report/{id}/download/`
Get signed download URL for the report file.

**Response**:
```json
{
  "download_url": "https://s3.../signed-url",
  "file_name": "discharge_summary_2024.pdf",
  "mime_type": "application/pdf"
}
```

---

### 3.5 Archive Report
**POST** `/report/{id}/archive/`
Archive a report.

```json
{
  "archive_reason": "Patient requested data removal"
}
```

---

### 3.6 Unarchive Report
**POST** `/report/{id}/unarchive/`
Restore an archived report.

---

## 4. Available Context Builders

These can be used in `context_config`:

### Single Objects (use FieldsConfigSpec):
- **patient** - Patient demographics
- **encounter** - Encounter details including care_team

### Querysets (use QuerysetConfigSpec):
- **allergies** - Allergy/intolerance records
- **diagnoses** - Diagnosis/condition records
- **symptoms** - Symptom records
- **medications** - Medication records
- **observations** - Observation records
- **file_uploads** - File attachments

---

## 5. Example Workflow

### Step 1: Get Available Fields
```bash
GET /template/schema/
```
Review the response to see what fields are available for each context builder.

### Step 2: Create Template
```bash
POST /template/
{
  "facility": null,
  "slug_value": "discharge-v1",
  "name": "Discharge Summary v1",
  "status": "active",
  "template_type": "discharge_summary",
  "default_format": "pdf",
  "template_data": "<h1>Discharge Summary</h1><p>Patient: {{ patient.name }}</p><p>Age: {{ patient.age }}</p><h2>Medications</h2><ul>{% for med in medications %}<li>{{ med.medication_name }}</li>{% endfor %}</ul>",
  "context_config": {
    "patient": {},
    "encounter": {},
    "medications": {
      "filters": {"status": "active"},
      "limit": 20
    }
  }
}
```

### Step 3: Generate Report
```bash
POST /report/generate/
{
  "template_id": "template-uuid-from-step-2",
  "report_type": "discharge_summary",
  "associating_id": "encounter-uuid",
  "encounter_id": "encounter-uuid",
  "patient_id": "patient-uuid",
  "output_format": "pdf"
}
```

### Step 4: Download Report
Wait for generation to complete, then:
```bash
GET /report/{report-id}/download/
```

---

## 6. Notes

- Templates must have `status: "active"` to generate reports
- Report generation is async - use webhooks/polling to check completion
- Context builders validate required dependencies (e.g., encounter builder needs `encounter_id`)
- Slugs are auto-prefixed: `f-{facility-uuid}-{slug}` for facility or `i-{slug}` for instance
- Templates use Jinja2 syntax for templating
- PDF generation uses WeasyPrint with customizable options
