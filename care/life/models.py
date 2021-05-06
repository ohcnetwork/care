import enum
from django.db import models
from django.db.models.fields import CharField
from django.contrib.postgres.fields import JSONField
from care.facility.models.base import BaseModel
from care.users.models import District, State


class JobStatus(enum.Enum):
    PENDING = "PENDING"
    WORKING = "WORKING"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


JobStatusChoices = [(e.value, e.name) for e in JobStatus]


class LifeDataManager(models.Manager):
    pass


class Job(BaseModel):
    file_url = models.URLField(null=False, blank=False)
    name = CharField(max_length=1024, default="")
    status = models.CharField(
        choices=JobStatusChoices, default=JobStatus.PENDING.value, blank=False, null=False, max_length=100
    )
    next_runtime = models.DateTimeField(auto_now_add=True)
    periodicity = models.IntegerField(default=10)  # in Mins
    contact_email = models.EmailField()
    last_errors = models.TextField(null=True, blank=True)
    suppress_emails = models.BooleanField(default=False)
    email_periodicity = models.IntegerField(default=10)  # in Mins
    email_next_sendtime = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Job Submitted by {self.contact_email} is currently in {self.status} status, to be next run at {self.next_runtime}"


class LifeData(BaseModel):
    created_job = models.ForeignKey(Job, on_delete=models.CASCADE, null=False, blank=False)
    data_id = models.CharField(max_length=1024, db_index=True, null=False, blank=False)
    category = models.CharField(max_length=1024, db_index=True, default="")
    data = JSONField(default=dict)
    phone_1 = models.CharField(max_length=200)
    district = models.ForeignKey(District, on_delete=models.PROTECT, null=False, blank=False)
    state = models.ForeignKey(State, on_delete=models.PROTECT, null=False, blank=False)
    is_duplicate = models.BooleanField(default=False)
    downvotes = models.IntegerField(default=0)
    upvotes = models.IntegerField(default=0)

    objects = LifeDataManager()
