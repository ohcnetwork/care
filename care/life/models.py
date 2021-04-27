import enum
from django.db import models
from django.db.models.fields import CharField
from care.facility.models.base import BaseModel
from care.users.models import District, State


class JobStatus(enum.Enum):
    PENDING = "PENDING"
    WORKING = "WORKING"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


JobStatusChoices = [(e.value, e.name) for e in JobStatus]


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

    def __str__(self):
        return f"Job Submitted by {self.contact_email} is currently in {self.status} status, to be next run at {self.next_runtime}"


class LifeData(BaseModel):
    created_job = models.ForeignKey(Job, on_delete=models.PROTECT, null=False, blank=False)
    data_id = models.IntegerField()
    title = models.TextField(default="")
    category = models.TextField(default="")
    resource_type = models.TextField(default="")
    description = models.TextField(default="")
    address = models.TextField(default="")
    phone_1 = models.TextField(default="")
    phone_2 = models.TextField(default="")
    email = models.TextField(default="")
    district = models.ForeignKey(District, on_delete=models.PROTECT, null=False, blank=False)
    state = models.ForeignKey(State, on_delete=models.PROTECT, null=False, blank=False)
    quantity_available = models.TextField(default="")
    price = models.TextField(default="")
    source_link = models.TextField(default="")
    comment = models.TextField(default="")
    created_on = models.TextField(default="")
    created_by = models.TextField(default="")
    Verified_by = models.TextField(default="")
    last_verified_on = models.TextField(default="")
    downvotes = models.IntegerField(default=0)
    upvotes = models.IntegerField(default=0)

