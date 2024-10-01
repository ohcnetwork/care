Environment Variables
=====================

``MIN_ENCOUNTER_DATE``
----------------------
Default value is `2020-01-01`. This is the minimum date for a possible consultation encounter.
Example: `MIN_ENCOUNTER_DATE=2000-01-01`

``TASK_SUMMARIZE_TRIAGE``
-------------------------
Default value is `True`. If set to `False`, the celery task to summarize triage data will not be executed.
Example: `TASK_SUMMARIZE_TRIAGE=False`

``TASK_SUMMARIZE_TESTS``
------------------------
Default value is `True`. If set to `False`, the celery task to summarize test data will not be executed.
Example: `TASK_SUMMARIZE_TESTS=False`

``TASK_SUMMARIZE_FACILITY_CAPACITY``
------------------------------------
Default value is `True`. If set to `False`, the celery task to summarize facility capacity data will not be executed.
Example: `TASK_SUMMARIZE_FACILITY_CAPACITY=False`

``TASK_SUMMARIZE_PATIENT``
--------------------------
Default value is `True`. If set to `False`, the celery task to summarize patient data will not be executed.
Example: `TASK_SUMMARIZE_PATIENT=False`

``TASK_SUMMARIZE_DISTRICT_PATIENT``
-----------------------------------
Default value is `True`. If set to `False`, the celery task to summarize district patient data will not be executed.
Example: `TASK_SUMMARIZE_DISTRICT_PATIENT=False`
