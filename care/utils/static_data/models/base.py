from abc import ABC

from django.conf import settings
from redis_om import HashModel, get_redis_connection


class BaseRedisModel(HashModel, ABC):
    class Meta:
        database = get_redis_connection(url=settings.REDIS_URL)
        global_key_prefix = "care_static_data"
