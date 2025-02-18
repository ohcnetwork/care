# ruff: noqa: SLF001
from django.db.models import Model
from django.utils import timezone


def enable_auto_time(*models: Model):
    for model in models:
        # enable auto_now_add and auto_now
        model._meta.get_field("created_date").auto_now_add = True
        model._meta.get_field("modified_date").auto_now = True
        # remove default
        model._meta.get_field("created_date").default = None
        model._meta.get_field("modified_date").default = None


def disable_auto_time(*models: Model):
    for model in models:
        # disable auto_now_add and auto_now
        model._meta.get_field("created_date").auto_now_add = False
        model._meta.get_field("modified_date").auto_now = False
        # set default to now
        model._meta.get_field("created_date").default = timezone.now
        model._meta.get_field("modified_date").default = timezone.now

    return lambda: enable_auto_time(*models)
