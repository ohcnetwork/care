# ruff: noqa: SLF001
import json
import logging
from typing import NamedTuple

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver

from care.audit_log.enums import Operation
from care.audit_log.helpers import (
    LogJsonEncoder,
    exclude_model,
    get_model_name,
    get_or_create_meta,
    remove_non_member_fields,
    seperate_hashable_dict,
)
from care.audit_log.middleware import AuditLogMiddleware

logger = logging.getLogger(__name__)


class Event(NamedTuple):
    model: str
    actor: AbstractUser
    entity_id: int | str
    changes: dict


@receiver(pre_delete, weak=False)
@receiver(pre_save, weak=False)
@transaction.atomic
def pre_save_signal(sender, instance, **kwargs) -> None:
    if not settings.AUDIT_LOG_ENABLED:
        return

    if not AuditLogMiddleware.is_request():
        logger.debug("Not a request")
        return

    model_name = get_model_name(instance)
    if exclude_model(model_name):
        logger.debug("%s ignored as per settings", model_name)
        return

    get_or_create_meta(instance)
    instance._meta.dal.event = None

    operation = Operation.UPDATE
    try:
        pre = sender.objects.get(pk=instance.pk)
    except ObjectDoesNotExist:
        # __dict__ is used on pre, therefore we need to create a function
        # that uses __dict__ too, but returns nothing.

        pre = lambda _: None  # noqa: E731
        operation = Operation.INSERT

    changes = {}

    if operation not in {Operation.INSERT, Operation.DELETE}:
        old, new = (
            remove_non_member_fields(pre.__dict__),
            remove_non_member_fields(instance.__dict__),
        )

        try:
            changes = dict(set(new.items()).difference(old.items()))
        except TypeError:  # handle non-hashable types
            old_hashable, old_non_hashable = seperate_hashable_dict(old)
            new_hashable, new_non_hashable = seperate_hashable_dict(new)

            changes = dict(set(new_hashable.items()).difference(old_hashable.items()))
            changes.update(
                {
                    k: v
                    for k, v in new_non_hashable.items()
                    if v != old_non_hashable.get(k)
                }
            )

        excluded_fields = settings.AUDIT_LOG["models"]["exclude"]["fields"].get(
            model_name, []
        )
        for field in excluded_fields:
            if field in changes:
                changes[field] = "xxx"

        if not changes:
            logger.debug("No changes for model. Ignoring.")
            return

    current_user = AuditLogMiddleware.get_current_user()

    instance._meta.dal.event = Event(
        model=model_name,
        actor=current_user,
        entity_id=instance.pk,
        changes=changes,
    )


def _post_processor(instance, event: Event | None, operation: Operation):
    request_id = AuditLogMiddleware.get_current_request_id()
    actor = AuditLogMiddleware.get_current_user()
    model_name = get_model_name(instance)

    if not event and operation != Operation.DELETE:
        logger.debug("Event not received for %s. Ignoring.", operation)
        return

    try:
        if operation == Operation.DELETE:
            changes = instance.__dict__
            if "_state" in changes:
                del changes["_state"]
        else:
            changes = json.dumps(event.changes if event else {}, cls=LogJsonEncoder)
    except Exception:
        logger.warning("Failed to log %s", event, exc_info=True)
        return

    logger.info(
        "AUDIT_LOG::%s|%s|%s|%s|ID:%s|%s",
        request_id,
        actor,
        operation.value,
        model_name,
        instance.pk,
        changes,
    )


@receiver(post_save, weak=False)
def post_save_signal(sender, instance, created, update_fields: frozenset, **kwargs):
    if not settings.AUDIT_LOG_ENABLED:
        return

    if not AuditLogMiddleware.is_request():
        logger.debug("Not a request")
        return

    model_name = get_model_name(instance)
    if exclude_model(model_name):
        logger.debug("Ignoring %s.", model_name)
        return

    operation = Operation.INSERT if created else Operation.UPDATE
    get_or_create_meta(instance)

    event = instance._meta.dal.event
    _post_processor(instance, event, operation)


@receiver(post_delete, weak=False)
def post_delete_signal(sender, instance, **kwargs) -> None:
    if not settings.AUDIT_LOG_ENABLED:
        return

    if not AuditLogMiddleware.is_request():
        logger.debug("Not a request")
        return

    model_name = get_model_name(instance)
    if exclude_model(model_name):
        logger.debug("Ignoring %s.", model_name)
        return

    event = instance._meta.dal.event
    _post_processor(instance, event, Operation.DELETE)
