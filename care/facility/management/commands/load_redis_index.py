from importlib import import_module

from django.core.cache import cache
from django.core.management import BaseCommand

from care.facility.static_data.icd11 import load_icd11_diagnosis
from care.facility.static_data.medibase import load_medibase_medicines
from plug_config import manager


class Command(BaseCommand):
    """
    Command to load static data to redis
    Usage: python manage.py load_redis_index
    """

    help = "Loads static data to redis"

    def handle(self, *args, **options):
        if cache.get("redis_index_loading"):
            self.stdout.write("Redis Index already loading, skipping")
            return

        cache.set("redis_index_loading", value=True, timeout=60 * 5)

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
                self.stdout.write(f"Module {module_path} not found")
            except Exception as e:
                self.stdout.write(f"Error loading static data for {plug.name}: {e}")

        cache.delete("redis_index_loading")
