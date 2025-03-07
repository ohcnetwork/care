# ruff: noqa: SLF001
from django.db.models import NOT_PROVIDED, Model
from django.utils import timezone


def enable_auto_time(*models: Model):
    """
    Enables automatic timestamping for the created and modified date fields in Django models.
    
    For each provided model, this function sets `auto_now_add` to True for the `created_date` field and `auto_now` to True for the `modified_date` field, ensuring that their timestamps are automatically managed. It also clears any default values by setting them to `NOT_PROVIDED`.
    """
    for model in models:
        # enable auto_now_add and auto_now
        model._meta.get_field("created_date").auto_now_add = True
        model._meta.get_field("modified_date").auto_now = True
        # remove default
        model._meta.get_field("created_date").default = NOT_PROVIDED
        model._meta.get_field("modified_date").default = NOT_PROVIDED


def disable_auto_time(*models: Model):
    """
    Disables automatic timestamping for the 'created_date' and 'modified_date' fields
    of the provided models.
    
    For each Django model, this function turns off automatic population of the timestamp
    fields by setting auto_now_add and auto_now to False and assigns timezone.now as the
    default value. It returns a lambda that, when called, restores the automatic timestamping
    by invoking enable_auto_time with the same models.
        
    Args:
        *models: Django model classes that include 'created_date' and 'modified_date' fields.
    
    Returns:
        A lambda function that re-enables automatic timestamp management for the provided models.
    """
    for model in models:
        # disable auto_now_add and auto_now
        model._meta.get_field("created_date").auto_now_add = False
        model._meta.get_field("modified_date").auto_now = False
        # set default to now
        model._meta.get_field("created_date").default = timezone.now
        model._meta.get_field("modified_date").default = timezone.now

    return lambda: enable_auto_time(*models)
