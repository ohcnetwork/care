from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from care.facility.api.serializers.asset import AssetConfigSerializer
from care.facility.models.asset import Asset
from care.facility.tasks.push_asset_config import (
    delete_asset_from_middleware_task,
    push_config_to_middleware_task,
)


@receiver(pre_save, sender=Asset)
def save_asset_fields_before_update(
    sender, instance, raw, using, update_fields, **kwargs
):
    if raw or instance.resolved_middleware is None:
        return

    if instance.pk:
        instance._previous_values = {  # noqa: SLF001
            "hostname": instance.resolved_middleware.get("hostname"),
        }


@receiver(post_save, sender=Asset)
def update_asset_config_on_middleware(
    sender, instance, created, raw, using, update_fields, **kwargs
):
    if (
        raw
        or (update_fields and "meta" not in update_fields)
        or (instance.resolved_middleware is None)
    ):
        return

    new_hostname = instance.resolved_middleware.get("hostname")
    old_hostname = getattr(instance, "_previous_values", {}).get("hostname")
    push_config_to_middleware_task.s(
        new_hostname,
        instance.external_id,
        AssetConfigSerializer(instance).data,
        old_hostname,
    )


@receiver(post_delete, sender=Asset)
def delete_asset_on_middleware(sender, instance, using, **kwargs):
    if instance.resolved_middleware is None:
        return
    hostname = instance.resolved_middleware.get("hostname")
    delete_asset_from_middleware_task.s(hostname, instance.external_id)
