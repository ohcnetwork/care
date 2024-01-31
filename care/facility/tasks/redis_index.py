from logging import Logger

from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.cache import cache

from care.facility.static_data.icd11 import load_icd11_diagnosis
from care.facility.static_data.medibase import load_medibase_medicines
from care.hcx.static_data.pmjy_packages import load_pmjy_packages
from care.utils.static_data.models.base import index_exists

logger: Logger = get_task_logger(__name__)


@shared_task
def load_redis_index():
    if cache.get("redis_index_loading"):
        logger.info("Redis Index already loading, skipping")
        return

    cache.set("redis_index_loading", True, timeout=60 * 2)
    logger.info("Loading Redis Index")
    if index_exists():
        logger.info("Index already exists, skipping")
        return

    load_icd11_diagnosis()
    load_medibase_medicines()
    load_pmjy_packages()

    cache.delete("redis_index_loading")
    logger.info("Redis Index Loaded")
