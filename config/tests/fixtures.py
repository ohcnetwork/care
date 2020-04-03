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
    s, _ = State.objects.get_or_create(id=1, name="Kerala")
    d, _ = District.objects.get_or_create(name="Kannur", state=s)
    return User.objects.create(
        user_type=10, district=d, phone_number="8887776665", gender=1, age=30, email="foo@foobar.com",
    )


@pytest.fixture()
def district_data():
    s, _ = State.objects.get_or_create(id=1, name="Kerala")
    for id, name in DISTRICT_CHOICES:
        District.objects.create(id=id, name=name, state=s)


@pytest.fixture()
def facility_data():
    s, _ = State.objects.get_or_create(id=1, name="Kerala")
    d, _ = District.objects.get_or_create(name="Kannur", state=s)
    return {
        "name": "Foo",
        "district": d.id,
        "facility_type": 1,
        "address": "8/88, 1st Cross, 1st Main, Boo Layout",
        "location": {"latitude": 49.878248, "longitude": 24.452545},
        "oxygen_capacity": 10,
        "phone_number": "9998887776",
    }
