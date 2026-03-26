# OHN CARE Backend For GSoC 2026: Setup & Contribution Log

## ✅ Phases 1-3: Setup Completed
The local CARE backend environment has been fully set up.
1. **Cloned the repository** into `d:\GSoC\care`
2. **Environment Setup:** Python 3.13 virtual environment `venv` activated.
3. **Dependencies Installed:** `pipenv sync` along with additional dependency handling on Windows (like `python-magic-bin` and disabling Redis temporarily since there is no local cache backend on WSL-less native Windows). Installed pre-commit hooks at `.git/hooks/pre-commit`.
4. **Setup Database:** PostgreSQL 17 running, role `care_user` and database `care` correctly initialized. Configured the `.env` settings. 
5. **Run Migrations:** Successfully applied database migrations using `python manage.py migrate`. (Applied dummy `WeasyPrint` and LocMemCache patches to bypass Windows limitations).
6. **Load Initial Data:** Populated database using `python manage.py load_fixtures` successfully!
7. **Created Admin User:** Superuser `myadmin` (email: myadmin@localhost) was created with password `password123`.
8. **Run Backend Server:** The development server is now running natively on process and you can confirm it's returning HTTP correctly at **`http://localhost:8000`** (Status: 403 by default for unauthenticated access on API).

---

## 🔎 9. Explore Codebase Structure
The backend uses **Django Rest Framework (DRF)**. Here is an overview of key files and directories:

* **`config/`**: Core infrastructure configuration. Contains main settings, authentication logic, middleware, and base urls.
* **`care/`**: This is where all the application code rests.
  * **`apps/`**: Code is decoupled into specific apps, such as `facility` (hospitals, doctors), `emr` (electronic medical records, patient encounters), `users`, etc.
  * **`models/`**: Defines the database schemas representing entities (e.g. `PatientRegistration`, `Facility`, `User`). 
  * **`views/` and `viewsets/`**: Handle incoming HTTP requests, process validation, and dictate what actions occur before a database transaction.
  * **`serializers/`**: Translate Python classes formatting the API inputs/outputs back and forth to JSON. They are the middleware defining structure validation between client and database.
  * **`api/`**: Declares Django Router endpoints binding URL paths with specific ViewSets.

---

## 🛤️ 10. Understand Request Flow (End-to-End Tracing)
Here is an example flow for the **Get Patients List** Endpoint (`GET /api/v1/patient/`):

1. **Request:** Client makes a GET request to `http://localhost:8000/api/v1/patient/`
2. **URL router (`config/urls.py` & `care/facility/api/urls.py`):** The URL path is parsed, matches `/api/v1/patient/` and directs the request to the registered **`PatientViewSet`**.
3. **View (`care/facility/api/viewsets/patient.py : PatientViewSet`):** The ViewSet receives the GET request. It enforces permissions (e.g., verifying user authentication/roles), applies filters (e.g., searching by name/facility), and paginates.
4. **Model (`care/facility/models/patient.py : PatientRegistration`):** For the returned QuerySet, the model constructs SQL queries under the hood hitting our PostgreSQL Database.
5. **Database (PostgreSQL):** Retrieves the raw structured records from `facility_patientregistration` tables.
6. **Serializer (`care/facility/api/serializers/patient.py : PatientListSerializer`):** Transforms the complex ORM objects into pure JSON layout structure, excluding private fields or formatting dates. 
7. **Response:** A 200 OK Response is dispatched containing a `results` array of serialized patients data back to the user browser.

---

## 👨‍💻 11 & 12. Contribution Preparation (Good First Issues)
If you view `https://github.com/ohcnetwork/care/issues`, here are 3 examples of excellent beginner/GSoC issues based on common historical patterns:

### **Issue 1: Add Pagination to an unpaginated internal API route**
* **Problem:** Some older admin API endpoints list results synchronously without limitation causing memory bloat.
* **Files to edit:** `care/*/api/viewsets/*.py` (Find the ViewSet missing `pagination_class`).
* **Implementation:** Import `CareLimitOffsetPagination` from `care.utils.pagination` and assign it to the target ViewSet class. Apply DB limits to serializers if necessary.

### **Issue 2: Improve the search/filtering of Facilities by Location/Pincode**
* **Problem:** Users need to narrow down `Facility` endpoints via Pincode filtering. Currently, it might not be indexed.
* **Files to edit:** `care/facility/api/viewsets/facility.py` (Filters).
* **Implementation:** Update or add a `FilterSet` targeting the `pincode` or `state` DB field using `django-filter` methods. Add index into model fields within `models/facility.py`.

### **Issue 3: Fix serialization missing fields (e.g. Include UpdatedBy in Audit logs)**
* **Problem:** The API JSON format for auditing isn't mapping `updated_by` relationships.
* **Files to edit:** `care/*/api/serializers/*.py`.
* **Implementation:** Add read-only model fields inside `Serializer.Meta.fields`. 

---

## 🌿 13. Git Workflow
To structure your PR strictly adhering to the GSoC process:

1. Create and switch to a descriptive branch based off of `develop`:
   ```bash
   git checkout -b fix/issue-number-feature-name
   ```
2. After editing `views/` or `serializers/`, stage and commit changes clearly:
   ```bash
   git add .
   git commit -m "Fix: Add missing updated_by serialization to user profile API"
   ```
3. Push to your forked repository and open a Pull Request mentioning `Fixes #XXX`:
   ```bash
   git push origin fix/issue-number-feature-name
   ```

---

## 🧹 14. Code Quality and Testing
* **Linting:** To adhere strictly to CARE backend standards seamlessly, run pre-commit locally against the lines you altered to catch spelling, typing hints (`ruff`), and code black stylistic auto-formating:
    ```bash
    pre-commit run --files $(git diff --name-only develop...HEAD)
    ```
* If failures occur, auto-formatters will usually solve them (e.g. double quotes to single quotes). After making corrections, you MUST re-stage `git add .` the specific file and run the command again.

🎉 Your setup is now functionally complete! You are ready to submit your first local backend PR!
