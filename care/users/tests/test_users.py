import pytest

from care.users.models import User


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
    def test_superuser_can_read_modify_delete_all(self, client, user, data):
        user.is_superuser = True
        user.save()

        response = client.post("/api/v1/users/", data,)
        assert response.status_code == 201

        client.force_authenticate(user=user)

        response = client.get("/api/v1/users/")
        assert response.status_code == 200
        assert response.json()["count"] == 2
        assert user.username in {r["username"] for r in response.json()["results"]}
        assert data["username"] in {r["username"] for r in response.json()["results"]}

        response = client.get(f"/api/v1/users/{data['username']}/")
        assert response.status_code == 200
        res_data = response.json()
        res_data.pop("id")
        password = data.pop("password")
        assert res_data == {
            **data,
            "district": 11,
            "gender": "Male",
            "user_type": "Doctor",
            "first_name": "",
            "last_name": "",
        }

        response = client.put(f"/api/v1/users/{data['username']}/", {**data, "age": 31, "password": password,})
        assert response.status_code == 200
        assert response.json()["age"] == 31
        assert User.objects.only("age").get(username=data["username"]).age == 31

        response = client.delete(f"/api/v1/users/{data['username']}/")
        assert response.status_code == 204
        with pytest.raises(User.DoesNotExist):
            User.objects.get(username=data["username"])

    def test_user_can_read_cant_modify_delete_others(self, client, user, data):
        response = client.post("/api/v1/users/", data,)
        assert response.status_code == 201

        client.force_authenticate(user=user)

        response = client.get("/api/v1/users/")
        assert response.status_code == 200
        assert response.json()["count"] == 2
        assert user.username in {r["username"] for r in response.json()["results"]}
        assert data["username"] in {r["username"] for r in response.json()["results"]}

        response = client.get(f"/api/v1/users/{data['username']}/")
        assert response.status_code == 200

        response = client.put(f"/api/v1/users/{data['username']}/", data)
        assert response.status_code == 404

        response = client.delete(f"/api/v1/users/{data['username']}/")
        assert response.status_code == 404

    def test_user_can_read_modify_delete_himself(self, client, data):
        response = client.post("/api/v1/users/", data,)
        assert response.status_code == 201

        user = User.objects.get(username=data["username"])
        client.force_authenticate(user=user)

        response = client.get("/api/v1/users/")
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert user.username in {r["username"] for r in response.json()["results"]}

        response = client.get(f"/api/v1/users/{user.username}/")
        assert response.status_code == 200

        response = client.put(f"/api/v1/users/{user.username}/", {**data, "age": 31,})
        assert response.status_code == 200
        assert response.json()["age"] == 31
        assert User.objects.only("age").get(username=data["username"]).age == 31

        response = client.delete(f"/api/v1/users/{user.username}/")
        assert response.status_code == 204
        with pytest.raises(User.DoesNotExist):
            User.objects.get(username=data["username"])
