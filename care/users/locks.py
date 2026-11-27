import logging
from contextlib import contextmanager

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from redis.exceptions import LockNotOwnedError, RedisError
from rest_framework.exceptions import APIException

from care.utils.lock import ObjectLocked

logger = logging.getLogger(__name__)


class UserAuthLockUnavailable(APIException):
    status_code = 503
    default_detail = "Authentication is temporarily unavailable. Please try again."
    default_code = "user_auth_lock_unavailable"


@contextmanager
def lock_user_auth(user_id):
    try:
        lock = cache.lock(f"lock:user_auth:{user_id}", timeout=settings.LOCK_TIMEOUT)
        acquired = lock.acquire(blocking=False)
    except RedisError as exc:
        raise UserAuthLockUnavailable from exc

    if not acquired:
        raise ObjectLocked

    def safe_release():
        try:
            lock.release()
        except LockNotOwnedError:
            logger.warning("User authentication lock expired before release")
        except RedisError:
            logger.exception("Unable to release user authentication lock")

    try:
        with transaction.atomic():
            yield
            try:
                # Verify ownership and leave a full lease for the outer commit.
                if not lock.reacquire():
                    raise ObjectLocked
            except LockNotOwnedError as exc:
                raise ObjectLocked from exc
            except RedisError as exc:
                raise UserAuthLockUnavailable from exc

        transaction.on_commit(safe_release, robust=True)
    except BaseException:
        safe_release()
        raise
