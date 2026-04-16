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


class MultipleItemsLock:
    def get_key(self, key):
        return f"lock:{key}"

    def __init__(self, keys, timeout=settings.LOCK_TIMEOUT):
        self.keys = [self.get_key(key) for key in keys]
        self.aquired_keys = []
        self.timeout = timeout

    def acquire(self):
        for key in self.keys:
            if not cache.set(key, value=True, timeout=self.timeout, nx=True):
                self.release()
                raise ObjectLocked
            self.aquired_keys.append(key)

    def release(self):
        for key in self.aquired_keys:
            cache.delete(key)

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
        return False
