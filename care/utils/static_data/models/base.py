from abc import ABC

from django.conf import settings
from redis_om import HashModel, get_redis_connection
from redis_om.model.migrations.migrator import schema_hash_key


class BaseRedisModel(HashModel, ABC):
    class Meta:
        database = get_redis_connection(url=settings.REDIS_URL)
        global_key_prefix = "care_static_data"


def index_exists(model: HashModel = None):
    """
    Checks the existence of a redisearch index.
    If no model is passed, it checks for the existence of any index.
    """

    conn = get_redis_connection(url=settings.REDIS_URL)
    if model:
        return conn.exists(schema_hash_key(model.Meta.index_name))
    return len(conn.execute_command("FT._LIST"))
