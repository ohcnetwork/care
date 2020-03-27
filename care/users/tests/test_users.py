# flake8: noqa

import pytest

from care.users.models import User
from config.tests.helper import client, user


@pytest.fixture()
def data():
    return {
        "user_type": 5,
        "email": "some.email@somedomain.com",
        "phone_number": "5554446667",
        "age": 30,
        "gender": 1,
        "district": 11,
        "username": "foo",
        "password": "bar",
    }


@pytest.mark.django_db(transaction=True)
class TestUser:
    def test_superuser_can_read_others(self, client, user, data):
        user.is_superuser = True
        user.save()
        client.force_authenticate(user=user)
        response = client.post("/api/v1/users/", data,)
        assert response.status_code == 201

        response = client.get(f"/api/v1/users/{data['username']}/")

        assert response.status_code == 200
        res_data = response.json()
        res_data.pop("id")
        data.pop("password")
        assert res_data == {
            **data,
            "district": "Kozhikode",
            "gender": "Male",
            "user_type": "Doctor",
            "first_name": "",
            "last_name": "",
            "skill": None,
        }

    def test_superuser_can_read_all(self, client, user, data):
        user.is_superuser = True
        user.save()
        client.force_authenticate(user=user)
        response = client.post("/api/v1/users/", data,)
        assert response.status_code == 201

        response = client.get("/api/v1/users/")

        assert response.status_code == 200
        assert response.json()["count"] == 2
        assert user.username in {r["username"] for r in response.json()["results"]}
        assert data["username"] in {r["username"] for r in response.json()["results"]}

    def test_superuser_can_modify_others(self, client, user, data):
        user.is_superuser = True
        user.save()
        client.force_authenticate(user=user)
        response = client.post("/api/v1/users/", data,)
        assert response.status_code == 201
        password = data.pop("password")

        response = client.put(f"/api/v1/users/{data['username']}/", {**data, "age": 31, "password": password,})

        assert response.status_code == 200
        assert response.json()["age"] == 31
        assert User.objects.only("age").get(username=data["username"]).age == 31

    def test_superuser_can_delete_others(self, client, user, data):
        user.is_superuser = True
        user.save()
        client.force_authenticate(user=user)
        response = client.post("/api/v1/users/", data,)
        assert response.status_code == 201

        response = client.delete(f"/api/v1/users/{data['username']}/")

        assert response.status_code == 204
        with pytest.raises(User.DoesNotExist):
            User.objects.get(username=data["username"])

    def test_user_can_read_oneself(self, client, data):
        response = client.post("/api/v1/users/", data,)
        assert response.status_code == 201
        user = User.objects.get(username=data["username"])
        client.force_authenticate(user=user)

        response = client.get(f"/api/v1/users/{user.username}/")

        assert response.status_code == 200

    def test_user_can_read_others(self, client, user, data):
        client.force_authenticate(user=user)
        response = client.post("/api/v1/users/", data,)
        assert response.status_code == 201

        response = client.get(f"/api/v1/users/{data['username']}/")

        assert response.status_code == 200

    def test_user_can_read_all(self, client, user, data):
        client.force_authenticate(user=user)
        response = client.post("/api/v1/users/", data,)
        assert response.status_code == 201

        response = client.get("/api/v1/users/")

        assert response.status_code == 200
        assert response.json()["count"] == 2
        assert user.username in {r["username"] for r in response.json()["results"]}
        assert data["username"] in {r["username"] for r in response.json()["results"]}

    def test_user_can_modify_oneself(self, client, data):
        response = client.post("/api/v1/users/", data,)
        assert response.status_code == 201
        user = User.objects.get(username=data["username"])
        client.force_authenticate(user=user)

        response = client.put(f"/api/v1/users/{user.username}/", {**data, "age": 31,})

        assert response.status_code == 200
        assert response.json()["age"] == 31
        assert User.objects.only("age").get(username=data["username"]).age == 31

    def test_user_cannot_modify_others(self, client, user, data):
        client.force_authenticate(user=user)
        response = client.post("/api/v1/users/", data,)
        assert response.status_code == 201

        response = client.put(f"/api/v1/users/{data['username']}/", data)

        assert response.status_code == 404

    def test_user_can_delete_oneself(self, client, data):
        response = client.post("/api/v1/users/", data,)
        assert response.status_code == 201
        user = User.objects.get(username=data["username"])
        client.force_authenticate(user=user)

        response = client.delete(f"/api/v1/users/{user.username}/")

        assert response.status_code == 204
        with pytest.raises(User.DoesNotExist):
            User.objects.get(username=data["username"])

    def test_user_cannot_delete_others(self, client, user, data):
        client.force_authenticate(user=user)
        response = client.post("/api/v1/users/", data,)
        assert response.status_code == 201

        response = client.delete(f"/api/v1/users/{data['username']}/")

        assert response.status_code == 404
