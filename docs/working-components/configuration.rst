Working Components
==================

This page explains the various components that make up the backend

Backend (Django)
----------------
The Backend is a Django application server with gunicorn, it uses the default gunicorn workers and processes count, It can only serve ( 2 * No of cores ) requests at a time per deployed instance, Since the application involves very little CPU, ideally The Backend Deployments need very little CPU and memory allocation. Increasing the number of gunicorn instances with the help of a load balancer can scale the application up.

Task Scheduler (celery beat)
----------------------------
This is a scheduler that schedules jobs at certain intervals similar to at Cron Job, The task scheduler is responsible for summarizing data at periodic intervals, the scheduler only schedules the job, it does not execute the actual job, because of this it is crucial that there is always only one instance of the scheduler running at any scale.

Task Worker (celery worker)
---------------------------
The celery worker is used to asynchronously execute code, The summary jobs are an example of a task that should be executed asynchronously. This project also creates notifications for events, produces discharge summaries which are all run as background tasks with celery. Celery requires a scheduler to schedule its tasks, by default it uses Redis to Schedule jobs and to store the results, this can be changed to use RabbitMq Instead. Using the database for this purpose is highly discouraged.

Database (PostgreSQL)
---------------------
Care uses a Postgresql database.

Cache (Redis)
-------------
Redis is used in a lot on API routes to cache data at the Request Layer, it is also used in various contexts to store intermediate query results, all permissions structures are cached in redis to avoid multiple queries to be executed on each API request, it is also intelligent enough to remove the caches when the permission model it describes changes.

Bucket (S3)
-----------
Care is built to use AWS S3 as the primary object storage but it can work with any provider that supports the S3 API, it primarily uses three buckets, one public bucket to store static data like CSS/js/images used by the Backend and one bucket stores facility data (e.g., Facility Cover Image). There is a private bucket to store confidential patient information, ideally, this bucket should have encryption at rest and encryption in transit enabled. Access to the patient bucket is given on request only through signed requests, Uploads also happen in a similar manner, The Upload mechanism randomizes names and removes all relations with the patient so that even in a worst-case scenario the damages can be minimalized.

SMS Gateway (AWS SNS)
---------------------
Care uses SNS as an SMS Gateway, the SMS feature is used for patient login via OTP and for Shifting updates.

Email Gateway (AWS SES)
-----------------------
Care uses emails to send discharge summaries, reset password tokens, and crash reports.

Reporting Infrastructure
------------------------
Since care by itself cannot produce a really detailed summary of its data, it is advised to use Metabase or Superset as external Business Intelligence tools and connect a Read Replica of the primary database with PII fields masked. This will allow much higher visibility into the actual data and make better data-driven decisions. If you are using Metabase you can ask the ohcnetwork team to share the existing dashboard structure for simplicity. Care Databases are designed to provide easy and configurable Reporting.
