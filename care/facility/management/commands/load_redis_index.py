from django.core.management import BaseCommand

from care.facility.static_data.icd11 import load_icd11_diagnosis
from care.facility.static_data.medibase import load_medibase_medicines
from care.hcx.static_data.pmjy_packages import load_pmjy_packages


class Command(BaseCommand):
    """
    Command to load static data to redis
    Usage: python manage.py load_redis_index
    """

    help = "Loads static data to redis"

    def handle(self, *args, **options):
        load_icd11_diagnosis()
        load_medibase_medicines()
        load_pmjy_packages()
