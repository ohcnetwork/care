from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from care.emr.models.scheduling.schedule import Schedule
from care.emr.utils.charge_item_definition import (
    recalculate_separately_billable,
    set_separately_billable_false,
)

_OLD_CHARGE_ITEM_DEF_ID = "_old_charge_item_definition_id"
_OLD_REVISIT_CHARGE_ITEM_DEF_ID = "_old_revisit_charge_item_definition_id"
_OLD_DELETED = "_old_deleted"


@receiver(pre_save, sender=Schedule)
def capture_old_charge_item_def_schedule(sender, instance, **kwargs):
    if instance.id:
        old_instance = Schedule.objects.get(id=instance.id)
        setattr(
            instance, _OLD_CHARGE_ITEM_DEF_ID, old_instance.charge_item_definition_id
        )
        setattr(
            instance,
            _OLD_REVISIT_CHARGE_ITEM_DEF_ID,
            old_instance.revisit_charge_item_definition_id,
        )
        setattr(instance, _OLD_DELETED, old_instance.deleted)
    else:
        setattr(instance, _OLD_CHARGE_ITEM_DEF_ID, None)
        setattr(instance, _OLD_REVISIT_CHARGE_ITEM_DEF_ID, None)
        setattr(instance, _OLD_DELETED, False)


@receiver(post_save, sender=Schedule)
def update_separately_billable_schedule(sender, instance, created, **kwargs):
    old_charge_item_def_id = getattr(instance, _OLD_CHARGE_ITEM_DEF_ID, None)
    new_charge_item_def_id = instance.charge_item_definition_id
    old_revisit_id = getattr(instance, _OLD_REVISIT_CHARGE_ITEM_DEF_ID, None)
    new_revisit_id = instance.revisit_charge_item_definition_id
    old_deleted = getattr(instance, _OLD_DELETED, False)

    is_soft_deleted = not old_deleted and instance.deleted

    if is_soft_deleted:
        if new_charge_item_def_id:
            recalculate_separately_billable(new_charge_item_def_id)
        if new_revisit_id:
            recalculate_separately_billable(new_revisit_id)
        return

    if old_charge_item_def_id and old_charge_item_def_id != new_charge_item_def_id:
        recalculate_separately_billable(old_charge_item_def_id)

    if new_charge_item_def_id and not instance.deleted:
        set_separately_billable_false(new_charge_item_def_id)

    if old_revisit_id and old_revisit_id != new_revisit_id:
        recalculate_separately_billable(old_revisit_id)

    if new_revisit_id and not instance.deleted:
        set_separately_billable_false(new_revisit_id)
