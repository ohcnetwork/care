from importlib import import_module
from logging import Logger

from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.cache import cache

from care.facility.static_data.icd11 import load_icd11_diagnosis
from care.facility.static_data.medibase import load_medibase_medicines
from care.utils.static_data.models.base import index_exists
from plug_config import manager

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

    for plug in manager.plugs:
        try:
            module_path = f"{plug.name}.static_data"
            module = import_module(module_path)

            load_static_data = getattr(module, "load_static_data", None)
            if load_static_data:
                load_static_data()
        except ModuleNotFoundError:
            logger.info(f"Module {module_path} not found")
        except Exception as e:
            logger.info(f"Error loading static data for {plug.name}: {e}")

    cache.delete("redis_index_loading")
    logger.info("Redis Index Loaded")
