from django.core.cache.backends import dummy, locmem
from django.core.cache.backends.base import DEFAULT_TIMEOUT


class DummyCache(dummy.DummyCache):
    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None, nx=False):
        return super().set(key, value, timeout, version)


class LocMemCache(locmem.LocMemCache):
    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None, nx=False):
        return super().set(key, value, timeout, version)
