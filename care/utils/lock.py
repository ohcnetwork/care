from django.conf import settings
from django.core.cache import cache
from rest_framework.exceptions import APIException


class ObjectLocked(APIException):
    status_code = 423
    default_detail = "The resource you are trying to access is locked"
    default_code = "object_locked"


class Lock:
    def __init__(self, key, timeout=settings.LOCK_TIMEOUT):
        self.key = f"lock:{key}"
        self.timeout = timeout

    def acquire(self):
        if not cache.set(self.key, value=True, timeout=self.timeout, nx=True):
            raise ObjectLocked

    def release(self):
        return cache.delete(self.key)

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
        return False
