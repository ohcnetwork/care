import contextlib

from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.timezone import now

from .models import UserFacilityAllocation


@receiver(pre_save, sender=settings.AUTH_USER_MODEL)
def save_fields_before_update(sender, instance, raw, using, update_fields, **kwargs):
    if raw:
        return

    if instance.pk:
        fields_to_save = {"home_facility"}
        if update_fields:
            fields_to_save &= set(update_fields)
        if fields_to_save:
            with contextlib.suppress(IndexError):
                instance._previous_values = instance.__class__._base_manager.filter(  # noqa SLF001
                    pk=instance.pk
                ).values(*fields_to_save)[0]


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def track_user_facility_allocation(
    sender, instance, created, raw, using, update_fields, **kwargs
):
    if raw or (update_fields and "home_facility" not in update_fields):
        return

    if created and instance.home_facility:
        UserFacilityAllocation.objects.create(
            user=instance, facility=instance.home_facility
        )
        return

    last_home_facility = getattr(instance, "_previous_values", {}).get("home_facility")

    if (
        last_home_facility and instance.home_facility_id != last_home_facility
    ) or instance.deleted:
        # this also includes the case when the user's new home facility is set to None
        UserFacilityAllocation.objects.filter(
            user=instance, facility=last_home_facility, end_date__isnull=True
        ).update(end_date=now())

    if instance.home_facility_id and instance.home_facility_id != last_home_facility:
        # create a new allocation if new home facility is changed
        UserFacilityAllocation.objects.create(
            user=instance, facility=instance.home_facility
        )
