from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from care.emr.models.product import Product
from care.emr.utils.charge_item_definition import (
    recalculate_separately_billable,
    set_separately_billable_false,
)

_OLD_CHARGE_ITEM_DEF_ID = "_old_charge_item_definition_id"
_OLD_DELETED = "_old_deleted"


@receiver(pre_save, sender=Product)
def capture_old_charge_item_def_product(sender, instance, **kwargs):
    if instance.id:
        old_instance = Product.objects.get(id=instance.id)
        setattr(
            instance, _OLD_CHARGE_ITEM_DEF_ID, old_instance.charge_item_definition_id
        )
        setattr(instance, _OLD_DELETED, old_instance.deleted)
    else:
        setattr(instance, _OLD_CHARGE_ITEM_DEF_ID, None)
        setattr(instance, _OLD_DELETED, False)


@receiver(post_save, sender=Product)
def update_separately_billable_product(sender, instance, created, **kwargs):
    old_charge_item_def_id = getattr(instance, _OLD_CHARGE_ITEM_DEF_ID, None)
    new_charge_item_def_id = instance.charge_item_definition_id
    old_deleted = getattr(instance, _OLD_DELETED, False)

    is_soft_deleted = not old_deleted and instance.deleted

    if is_soft_deleted and new_charge_item_def_id:
        recalculate_separately_billable(new_charge_item_def_id)
        return

    if old_charge_item_def_id and old_charge_item_def_id != new_charge_item_def_id:
        recalculate_separately_billable(old_charge_item_def_id)

    if new_charge_item_def_id and not instance.deleted:
        set_separately_billable_false(new_charge_item_def_id)
