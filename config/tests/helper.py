import pytest
from rest_framework.test import APIClient


from care.users.models import User


@pytest.fixture()
def client():
    client = APIClient()
    client.default_format = "json"
    return client


@pytest.fixture()
def user():
    return User.objects.create(
        user_type=5,
        district=13,
        phone_number="8887776665",
        gender=1,
        age=30,
        email="foo@foobar.com",
    )
