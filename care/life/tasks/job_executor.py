import csv
import json
from datetime import timedelta

import boto3
import requests
from celery.decorators import periodic_task
from celery.schedules import crontab
from django.conf import settings
from django.db.models import fields
from django.utils.timezone import localtime, now
from rest_framework import serializers

from care.life.models import Job, JobStatus, LifeData
from care.users.models import District, State

rows_header = [
    "id",
    "title",
    "category",
    "resource type",
    "address",
    "phone_1",
    "phone_2",
    "email",
    "district",
    "state",
    "quantity_available",
    "price",
    "source_link",
    "comment",
    "created_on",
    "created_by",
    "verified_by",
    "last_verified_on",
    "description",
]


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
            mapped_data = get_mapped_data(mapping, row)
            mapped_data["deleted"] = False
            validated_obj = get_validated_object(mapped_data, job)
        except Exception as e:
            print(e)
            errors += str(e) + f" for row {row} \n"
            continue
        validated_obj.save()
    LifeData.objects.filter(deleted=True).delete()
    job.last_errors = errors
    job.next_runtime = localtime(now()) + timedelta(minutes=job.periodicity)
    job.status = JobStatus.PENDING.value
    job.save()


def get_validated_object(data, job):
    state = State.objects.filter(name__icontains=data["state"]).first()
    if not state:
        raise Exception(f"State {data['state']} is not defined")

    district = District.objects.filter(name__icontains=data["district"], state=state).first()
    if not district:
        raise Exception(f"District {data['district']} is not defined")

    existing_obj = LifeData.objects.filter(created_job=job, data_id=data["id"]).first()
    data["state"] = state
    data["district"] = district
    data["category"] = data["category"].lower()
    if not existing_obj:
        existing_obj = LifeData()
    data["data_id"] = data["id"]
    del data["id"]
    for field in data:
        setattr(existing_obj, field, data[field])
    existing_obj.created_job = job
    return existing_obj


def get_mapped_data(mapping, row):
    validated_row = {}
    for header in rows_header:
        validated_row[header] = row[mapping[header]]
    return validated_row


def get_mapping(row):
    mapping = {}
    for j, i in enumerate(row):
        if i in rows_header:
            mapping[i] = j
    if len(mapping.keys()) != len(rows_header):
        raise Exception("Fields Missing in Header")
    return mapping


@periodic_task(run_every=crontab(minute="*/2"))
def run_jobs():
    jobs = Job.objects.filter(status=JobStatus.PENDING.value, next_runtime__lte=localtime(now()))
    for job in jobs:
        # Add Concurrency Locks if needed
        parse_file(job)


class LifeDataSerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source="state.name")
    district_name = serializers.CharField(source="district.name")

    class Meta:
        model = LifeData
        fields = "__all__"


@periodic_task(run_every=crontab(minute="*/30"))
def save_life_data():
    categories = LifeData.objects.all().select_related("state", "district").distinct("category")
    for category in categories:
        category = category.category
        data = LifeDataSerializer(LifeData.objects.filter(category=category), many=True).data

        s3 = boto3.resource(
            "s3",
            endpoint_url=settings.LIFE_S3_ENDPOINT,
            aws_access_key_id=settings.LIFE_S3_ACCESS_KEY,
            aws_secret_access_key=settings.LIFE_S3_SECRET,
        )
        s3object = s3.Object(settings.LIFE_S3_BUCKET, f"{category}.json")

        s3object.put(ACL="public-read", Body=(bytes(json.dumps(data).encode("UTF-8"))))
