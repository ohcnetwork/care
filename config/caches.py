from django.core.cache.backends import dummy, locmem
from django.core.cache.backends.base import DEFAULT_TIMEOUT


class DummyCache(dummy.DummyCache):
    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None, nx=None):
        super().set(key, value, timeout, version)
        # mimic the behavior of django_redis with setnx, for tests
        return True


class LocMemCache(locmem.LocMemCache):
    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None, nx=None):
        super().set(key, value, timeout, version)
        # mimic the behavior of django_redis with setnx, for tests
        return True
