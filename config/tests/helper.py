import pytest
from rest_framework.test import APIClient


@pytest.fixture()
def client():
    client = APIClient()
    client.default_format = "json"
    return client
