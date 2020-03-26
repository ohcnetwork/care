import pytest

from django.conf import settings
from config.settings.test import DATABASES

@pytest.fixture(scope='session')
def django_db_setup():
    settings.DATABASES = DATABASES
