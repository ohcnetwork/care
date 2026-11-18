from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.test import SimpleTestCase

from config.caches import TestRedisCache


class CacheIsolationTests(SimpleTestCase):
    def make_cache(self, namespace):
        params = deepcopy(settings.CACHES["default"])
        params["KEY_PREFIX"] = f"cache-isolation-tests:{uuid4().hex}:{namespace}"
        params["OPTIONS"]["IGNORE_EXCEPTIONS"] = False
        backend = TestRedisCache(params.pop("LOCATION"), params)
        self.addCleanup(backend.close)
        self.addCleanup(backend.clear)
        return backend

    def test_worker_keys_use_current_process_after_fork(self):
        backend = self.make_cache("keys")

        with patch("config.caches.os.getpid", return_value=101):
            parent_key = backend.make_key("shared-key")
        with patch("config.caches.os.getpid", return_value=102):
            worker_key = backend.make_key("shared-key")

        self.assertEqual(parent_key, f"{backend.key_prefix}:101:1:shared-key")
        self.assertEqual(worker_key, f"{backend.key_prefix}:102:1:shared-key")

    def test_clear_preserves_other_worker_values_and_auth_locks(self):
        first = self.make_cache("first")
        second = self.make_cache("second")
        first.set("shared-key", "first")
        second.set("shared-key", "second")
        first_lock = first.lock("lock:user_auth:shared-user", timeout=30)
        second_lock = second.lock("lock:user_auth:shared-user", timeout=30)

        try:
            self.assertTrue(first_lock.acquire(blocking=False))
            self.assertTrue(second_lock.acquire(blocking=False))

            second.clear()

            self.assertIsNone(second.get("shared-key"))
            self.assertFalse(second_lock.owned())
            self.assertEqual(first.get("shared-key"), "first")
            self.assertTrue(first_lock.owned())
        finally:
            for lock in (first_lock, second_lock):
                if lock.owned():
                    lock.release()
