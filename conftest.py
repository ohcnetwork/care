import pytest
from django.conf import settings

from config.settings.test import DATABASES
from config.tests.fixtures import client, district_data, user  # noqa


@pytest.fixture(scope="session")
def django_db_setup():
    settings.DATABASES = DATABASES
