import csv
import io
import json
from datetime import timedelta
from os import error

import boto3
import requests
from celery.decorators import periodic_task
from celery.schedules import crontab
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils.timezone import localtime, now
from rest_framework import serializers

from care.life.api.serializers.lifedata import LifeDataSerializer
from care.life.models import Job, JobStatus, LifeData
from care.users.models import District, State

rows_header = [
    "id",
    "title",
    "category",
    "resource type",
    "address",
    "description",
    "phone_1",
    "phone_2",
    "email",
    "district",
    "state",
    "quantity_available",
    "price",
    "source_link",
    "comment",
    "created_by",
    "created_on",
    "verified_by",
    "last_verified_on",
    "pincode",
    "verification_status",
    "city",
    "hospital_available_normal_beds",
    "hospital_available_oxygen_beds",
    "hospital_available_icu_beds",
    "hospital_available_ventilator_beds",
]

required_headers = [
    "id",
    "title",
    "category",
    "phone_1",
    "district",
    "state",
]

choices_validation = [
    {"key": "category", "choices": ["oxygen", "medicine", "hospital", "ambulance", "helpline", "vaccine", "food"]}
]


def send_email(file_name, errors, email_id):
    errors = errors.replace("\n", "<br>")
    msg = EmailMessage(
        f"CARE | CSV Parsing Errors for {file_name}",
        f"Following are the errors <br> {errors}",
        settings.DEFAULT_FROM_EMAIL,
        (email_id,),
    )
    msg.content_subtype = "html"  # Main content is now text/html
    msg.send()


def parse_file(job):
    job.status = JobStatus.WORKING.value
    job.save()
    response = requests.get(job.file_url)
    decoded_content = response.content.decode("utf-8")
    csv_rows = csv.reader(decoded_content.splitlines(), delimiter=",")
    mapping = {}
    start = 1
    errors = ""
    LifeData.objects.filter(created_job=job).update(deleted=True)
    for row in csv_rows:
        try:
            if start:
                mapping = get_mapping(row)
                start = 0
                continue
            mapped_data = get_mapped_data(mapping, row)
            mapped_data["deleted"] = False
            validated_obj = get_validated_object(mapped_data, job)
        except Exception as e:
            # print(e)
            errors += str(e) + f" for row {row} \n"
            if start:
                break
            continue
        validated_obj.deleted = False
        validated_obj.save()
    LifeData.objects.filter(deleted=True).delete()
    job.last_errors = errors
    job.next_runtime = localtime(now()) + timedelta(minutes=job.periodicity)
    job.status = JobStatus.PENDING.value
    job.save()
    if (not job.suppress_emails) and job.email_next_sendtime < localtime(now()):
        job.email_next_sendtime = localtime(now()) + timedelta(minutes=job.email_periodicity)
        job.save()
        if errors:
            send_email(job.name, errors, job.contact_email)


def check_data_change(row_data, existing_data):
    fields = ["last_verified_on", "verified_by", "verification_status"]
    for field in fields:
        if existing_data.get(field, "") != row_data.get(field, ""):
            return True
    return False


def get_validated_object(data, job):

    for field in required_headers:
        if len(data[field].strip()) == 0:
            raise Exception(f"Field {field} is required. ")
    data["category"] = data["category"].lower()
    for validation in choices_validation:
        if data[validation["key"]] not in validation["choices"]:
            raise Exception(f"Choice {data[validation['key']]} is not valid for field {validation['key']} ")

    state = State.objects.filter(name__icontains=data["state"]).first()
    if not state:
        raise Exception(f"State {data['state']} is not defined")
    del data["state"]
    district = District.objects.filter(name__icontains=data["district"], state=state).first()
    if not district:
        raise Exception(f"District {data['district']} is not defined")
    del data["district"]

    existing_obj = LifeData.objects.filter(created_job=job, data_id=data["id"]).first()
    existing_obj_exists = existing_obj is not None
    if not existing_obj:
        existing_obj = LifeData()

    duplicate_objs = LifeData.objects.filter(
        category=data["category"], phone_1=data["phone_1"], state=state, district=district
    )
    if duplicate_objs.exists():
        data_has_changed = False
        if existing_obj_exists:
            data_has_changed = check_data_change(data, existing_obj.data)
        else:
            data_has_changed = True
        if data_has_changed:
            duplicate_objs.update(is_duplicate=True)
            existing_obj.is_duplicate = False
    else:
        existing_obj.is_duplicate = False

    phone_1 = data["phone_1"]
    del data["phone_1"]
    existing_obj.phone_1 = phone_1

    existing_obj.data_id = data["id"]
    existing_obj.state = state
    existing_obj.district = district
    existing_obj.category = data["category"]
    del data["category"]
    del data["id"]
    existing_obj.data = data
    existing_obj.created_job = job
    return existing_obj


def get_mapped_data(mapping, row):
    validated_row = {}
    for header in list(mapping.keys()):
        if len(header.strip()) == 0:
            continue
        validated_row[header] = row[mapping[header]]
    return validated_row


def get_mapping(row):
    mapping = {}
    for j, i in enumerate(row):
        mapping[i.strip()] = j
    for field in required_headers:
        if field not in mapping:
            raise Exception(f"Field {field} not present ")
    return mapping


@periodic_task(run_every=crontab(minute="*/2"))
def run_jobs():
    jobs = Job.objects.filter(status=JobStatus.PENDING.value, next_runtime__lte=localtime(now()))
    for job in jobs:
        # Add Concurrency Locks if needed
        parse_file(job)


@periodic_task(run_every=crontab(minute="*/30"))
def save_life_data():
    categories = LifeData.objects.all().select_related("state", "district").distinct("category")
    for category in categories:
        category = category.category
        serialized_data = LifeDataSerializer(
            LifeData.objects.filter(category=category, is_duplicate=False), many=True
        ).data
        all_headers = {}
        for index in range(len(serialized_data)):
            data = dict(serialized_data[index])
            data.update(data["data"])
            del data["data"]
            serialized_data[index] = data
            all_headers.update(data)
        # Create CSV File
        csv_file = io.StringIO()
        writer = csv.DictWriter(csv_file, fieldnames=all_headers.keys())
        writer.writeheader()
        writer.writerows(serialized_data)
        csv_data = csv_file.getvalue()
        # Write CSV and Json to S3
        s3 = boto3.resource(
            "s3",
            endpoint_url=settings.LIFE_S3_ENDPOINT,
            aws_access_key_id=settings.LIFE_S3_ACCESS_KEY,
            aws_secret_access_key=settings.LIFE_S3_SECRET,
        )
        s3_json_object = s3.Object(settings.LIFE_S3_BUCKET, f"{category}.json")
        s3_json_object.put(ACL="public-read", Body=(bytes(json.dumps(serialized_data).encode("UTF-8"))))

        s3_csv_object = s3.Object(settings.LIFE_S3_BUCKET, f"{category}.csv")
        s3_csv_object.put(ACL="public-read", Body=csv_data)

