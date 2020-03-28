import pytest
from rest_framework.test import APIClient

from care.users.models import DISTRICT_CHOICES, District, State, User


@pytest.fixture()
def client():
    client = APIClient()
    client.default_format = "json"
    return client


@pytest.fixture()
def user():
    return User.objects.create(
        user_type=5, district=13, phone_number="8887776665", gender=1, age=30, email="foo@foobar.com",
    )


@pytest.fixture()
def district_data():
    s = State.objects.create(id=1, name="KL")
    for id, name in DISTRICT_CHOICES:
        District.objects.create(id=id, name=name, state=s)
