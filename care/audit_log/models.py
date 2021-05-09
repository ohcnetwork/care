from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import Index, UniqueConstraint

from care.audit_log.enums import DjangoOperations
from care.audit_log.helpers import LogJsonEncoder

UserModel = get_user_model()


class Request(models.Model):
    request_id = models.CharField(max_length=100)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=511)
    actor = models.ForeignKey(UserModel, on_delete=models.PROTECT)
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [UniqueConstraint(fields=["request_id"], name="al_request__uniq__request_id")]
        indexes = [Index(fields=["request_id"], name="al_request__idx__request_id")]


class Log(models.Model):
    request = models.ForeignKey(Request, on_delete=models.PROTECT)
    operation = models.IntegerField(choices=DjangoOperations)

    model = models.CharField(max_length=127)
    entity_id = models.CharField(max_length=127)

    changes = JSONField(default=dict, encoder=LogJsonEncoder)
