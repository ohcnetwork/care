import os

from django.core.cache.backends import dummy, locmem
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django_redis.cache import RedisCache


def test_cache_key(key, key_prefix, version):
    # Resolve the process ID here because test workers can inherit the cache backend.
    return f"{key_prefix}:{os.getpid()}:{version}:{key}"


class TestRedisCache(RedisCache):
    def clear(self):
        """Clear this test worker's keys without flushing other workers' locks."""
        return self.delete_pattern("*")


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
