# ruff: noqa: SLF001
from django.db.models import Model
from django.utils import timezone


def enable_auto_time(*models: Model):
    for model in models:
        created_field = model._meta.get_field("created_date")
        modified_field = model._meta.get_field("modified_date")
        delattr(created_field, "default")
        delattr(modified_field, "default")
        created_field.auto_now_add = True
        modified_field.auto_now = True


def disable_auto_time(*models: Model):
    for model in models:
        created_field = model._meta.get_field("created_date")
        modified_field = model._meta.get_field("modified_date")
        delattr(created_field, "auto_now_add")
        delattr(modified_field, "auto_now")
        created_field.default = timezone.now
        modified_field.default = timezone.now

    return lambda: enable_auto_time(*models)
