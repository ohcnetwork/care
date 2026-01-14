import uuid
from typing import Any

from django.test import override_settings


class OverrideCache(override_settings):
    """
    Overrides the cache settings for the test to use a
    local memory cache instead of the redis cache
    """

    def __init__(self, decorated):
        self.decorated = decorated
        super().__init__(
            CACHES={
                "default": {
                    "BACKEND": "config.caches.LocMemCache",
                    "LOCATION": f"care-test-{uuid.uuid4()}",
                }
            },
        )

    def __call__(self) -> Any:
        return super().__call__(self.decorated)
