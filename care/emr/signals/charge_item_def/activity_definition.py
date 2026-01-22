from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from care.emr.models.activity_definition import ActivityDefinition
from care.emr.utils.charge_item_definition import (
    recalculate_separately_billable,
    set_separately_billable_false,
)

_OLD_CHARGE_ITEM_DEFS_IDS = "_old_charge_item_definitions"
_OLD_DELETED = "_old_deleted"


@receiver(pre_save, sender=ActivityDefinition)
def capture_old_charge_item_defs_activity(sender, instance, **kwargs):
    if instance.id:
        old_instance = ActivityDefinition.objects.get(id=instance.id)
        setattr(
            instance,
            _OLD_CHARGE_ITEM_DEFS_IDS,
            list(old_instance.charge_item_definitions or []),
        )
        setattr(instance, _OLD_DELETED, old_instance.deleted)
    else:
        setattr(instance, _OLD_CHARGE_ITEM_DEFS_IDS, [])
        setattr(instance, _OLD_DELETED, False)


@receiver(post_save, sender=ActivityDefinition)
def update_separately_billable_activity(sender, instance, created, **kwargs):
    old_ids = set(getattr(instance, _OLD_CHARGE_ITEM_DEFS_IDS, []) or [])
    new_ids = set(instance.charge_item_definitions or [])
    old_deleted = getattr(instance, _OLD_DELETED, False)

    is_soft_deleted = not old_deleted and instance.deleted

    if is_soft_deleted:
        for charge_item_def_id in new_ids:
            recalculate_separately_billable(charge_item_def_id)
        return

    added_ids = new_ids - old_ids
    for charge_item_def_id in added_ids:
        if not instance.deleted:
            set_separately_billable_false(charge_item_def_id)

    removed_ids = old_ids - new_ids
    for charge_item_def_id in removed_ids:
        recalculate_separately_billable(charge_item_def_id)
