import re

import pytest
from django.contrib.gis.geos import Point

from care.facility.models import District, Facility, FacilityCapacity, FacilityLocalGovtBody, State
from care.users.models import User
from config.tests.helper import assert_equal_dicts, mock_equal

# flake8: noqa


@pytest.fixture()
def user_data():
    return dict(
        username="bar",
        user_type=5,
        district_id=13,
        phone_number="8887776664",
        gender=1,
        age=30,
        email="bar@foobar.com",
    )


@pytest.fixture()
def facility():
    f = Facility.objects.create(
        name="Foo",
        district=District(id=13, name="Kannur", state=State(id=1, name="Kerala")),
        facility_type=1,
        address="8/88, 1st Cross, 1st Main, Boo Layout",
        location=Point(24.452545, 49.878248),
        oxygen_capacity=10,
        phone_number="9998887776",
    )
    FacilityLocalGovtBody.objects.create(facility=f, local_body=None, district_id=13)
    return f


@pytest.mark.usefixtures("district_data")
@pytest.mark.django_db(transaction=True)
class TestFacility:
    def test_login_required(self, client):
        response = client.post("/api/v1/facility/", {},)
        assert response.status_code == 403

    def test_create(self, client, user, facility_data):
        client.force_authenticate(user=user)
        response = client.post("/api/v1/facility/", facility_data,)

        assert response.status_code == 201

        assert assert_equal_dicts(
            response.json(),
            {
                **facility_data,
                "id": mock_equal,
                "facility_type": "Educational Inst",
                "local_body": None,
                "local_body_object": None,
                "district": facility_data["district"],
                "district_object": {"id": facility_data["district"], "name": "Kannur", "state": mock_equal},
                "state": mock_equal,
                "state_object": {"id": mock_equal, "name": "Kerala"},
                "created_date": mock_equal,
                "modified_date": mock_equal,
            },
        )

        facility = Facility.objects.get(
            name=facility_data["name"],
            district=facility_data["district"],
            facility_type=facility_data["facility_type"],
            address=facility_data["address"],
            oxygen_capacity=facility_data["oxygen_capacity"],
            phone_number=facility_data["phone_number"],
            created_by=user,
        )
        assert facility
        assert facility.location.tuple == (
            facility_data["location"]["longitude"],
            facility_data["location"]["latitude"],
        )

    def test_active_check(self, client, user, facility):
        client.force_authenticate(user=user)
        facility.created_by = user
        facility.is_active = False
        facility.save()
        response = client.get(f"/api/v1/facility/{facility.id}/")
        assert response.status_code == 404

    def test_retrieve(self, client, user, facility):
        client.force_authenticate(user=user)
        facility.created_by = user
        facility.save()
        response = client.get(f"/api/v1/facility/{facility.id}/")
        assert response.status_code == 200

        assert response.json() == {
            "id": facility.id,
            "name": facility.name,
            "facility_type": "Educational Inst",
            "address": facility.address,
            "location": {"latitude": facility.location.tuple[1], "longitude": facility.location.tuple[0],},
            "local_body": None,
            "local_body_object": None,
            "district": 13,
            "district_object": {"id": 13, "name": "Kannur", "state": 1},
            "state": mock_equal,
            "state_object": {"id": mock_equal, "name": "Kerala"},
            "oxygen_capacity": facility.oxygen_capacity,
            "phone_number": facility.phone_number,
            "created_date": mock_equal,
            "modified_date": mock_equal,
        }

    def test_update(self, client, user, facility):
        client.force_authenticate(user=user)
        facility.created_by = user
        facility.save()

        new_district = {"id": 12, "name": "Wayanad"}

        response = client.put(
            f"/api/v1/facility/{facility.id}/",
            {
                "name": "Another name",
                "district": new_district["id"],
                "facility_type": facility.facility_type,
                "address": facility.address,
            },
        )
        assert response.status_code == 200
        assert response.json() == {
            "id": facility.id,
            "name": "Another name",
            "facility_type": "Educational Inst",
            "address": facility.address,
            "location": {"latitude": facility.location.tuple[1], "longitude": facility.location.tuple[0],},
            "local_body": None,
            "local_body_object": None,
            "district": new_district["id"],
            "district_object": {"id": new_district["id"], "name": new_district["name"], "state": 1},
            "state": mock_equal,
            "state_object": {"id": mock_equal, "name": "Kerala"},
            "oxygen_capacity": facility.oxygen_capacity,
            "phone_number": facility.phone_number,
            "created_date": mock_equal,
            "modified_date": mock_equal,
        }
        facility.refresh_from_db()
        assert facility.name == "Another name"

    def test_update_doesnt_change_creator(self, client, user, user_data, facility, facility_data):
        facility.created_by = User.objects.create(**user_data)
        facility.save()
        original_creator = facility.created_by

        user.is_superuser = True
        user.save()
        client.force_authenticate(user=user)

        response = client.put(f"/api/v1/facility/{facility.id}/", facility_data)
        assert response.status_code == 200
        facility.refresh_from_db()
        assert facility.created_by == original_creator

    def test_destroy(self, client, user, facility):
        client.force_authenticate(user=user)
        facility.created_by = user
        facility.save()

        response = client.delete(f"/api/v1/facility/{facility.id}/",)
        assert response.status_code == 403

        user.is_superuser = True
        user.save()
        response = client.delete(f"/api/v1/facility/{facility.id}/",)
        assert response.status_code == 204
        with pytest.raises(Facility.DoesNotExist):
            Facility.objects.get(id=facility.id)

    def test_list(self, client, user, facility):
        client.force_authenticate(user=user)
        facility.created_by = user
        facility.save()
        response = client.get(f"/api/v1/facility/")
        assert response.status_code == 200
        assert response.json() == {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": facility.id,
                    "name": facility.name,
                    "facility_type": "Educational Inst",
                    "address": facility.address,
                    "location": {"latitude": facility.location.tuple[1], "longitude": facility.location.tuple[0],},
                    "local_body": None,
                    "local_body_object": None,
                    "district": facility.district.id,
                    "district_object": {
                        "id": facility.district.id,
                        "name": facility.district.name,
                        "state": facility.district.state.id,
                    },
                    "state": facility.state.id,
                    "state_object": {"id": facility.state.id, "name": facility.state.name},
                    "oxygen_capacity": facility.oxygen_capacity,
                    "phone_number": facility.phone_number,
                    "created_date": mock_equal,
                    "modified_date": mock_equal,
                },
            ],
        }

    def test_list_all(self, client, user, facility):
        client.force_authenticate(user=user)
        response = client.get(f"/api/v1/facility/")
        assert response.status_code == 200
        assert response.json() == {"count": 0, "next": None, "previous": None, "results": []}

        response = client.get(f"/api/v1/facility/?all=true")
        assert response.json() == {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": facility.id,
                    "name": facility.name,
                    "facility_type": {"id": facility.facility_type, "name": "Educational Inst",},
                    "local_body": None,
                    "local_body_object": None,
                    "district": facility.district.id,
                    "district_object": {
                        "id": facility.district.id,
                        "name": facility.district.name,
                        "state": facility.district.state.id,
                    },
                    "state": facility.state.id,
                    "state_object": {"id": facility.state.id, "name": facility.state.name},
                },
            ],
        }


@pytest.mark.usefixtures("district_data")
@pytest.mark.django_db(transaction=True)
class TestFacilityBulkUpsert:
    def test_success(self, client, user, facility):
        capacity = FacilityCapacity.objects.create(
            facility=facility, room_type=1, total_capacity=50, current_capacity=0
        )
        facility.created_by = user
        facility.save()
        user.is_superuser = True
        user.save()
        client.force_authenticate(user=user)

        name = "Another"
        address = "Dasappan's House, Washington Jn, OolaMukk P.O."
        phone_number = "7776665554"
        response = client.post(
            "/api/v1/facility/bulk_upsert/",
            data=[
                {
                    "name": facility.name,
                    "district": facility.district.id,
                    "facility_type": 3,
                    "address": facility.address,
                    "capacity": [{"room_type": 1, "total_capacity": 100, "current_capacity": 48,}],
                },
                {
                    "name": name,
                    "district": 1,
                    "facility_type": 2,
                    "address": address,
                    "phone_number": phone_number,
                    "capacity": [
                        {"room_type": 0, "total_capacity": 350, "current_capacity": 150,},
                        {"room_type": 1, "total_capacity": 200, "current_capacity": 100,},
                    ],
                },
            ],
        )
        assert response.status_code == 204

        facility.refresh_from_db()
        assert facility.facility_type == 3
        capacities = facility.facilitycapacity_set.all()
        assert capacities[0].id == capacity.id
        assert capacities[0].room_type == 1
        assert capacities[0].total_capacity == 100
        assert capacities[0].current_capacity == 48
        assert len(capacities) == 1

        new_facility = Facility.objects.get(
            created_by=user, name=name, district_id=1, facility_type=2, address=address, phone_number=phone_number,
        )
        assert new_facility
        capacities = new_facility.facilitycapacity_set.all()
        assert capacities[0].room_type == 0
        assert capacities[0].total_capacity == 350
        assert capacities[0].current_capacity == 150
        assert capacities[1].room_type == 1
        assert capacities[1].total_capacity == 200
        assert capacities[1].current_capacity == 100
        assert len(capacities) == 2

    def test_super_user_access(self, client, user, facility):
        client.force_authenticate(user=user)
        response = client.get(f"/api/v1/facility/{facility.id}/")
        assert response.status_code == 404

        user.is_superuser = True
        user.save()
        response = client.get(f"/api/v1/facility/{facility.id}/")
        assert response.status_code == 200
        assert response.json() == {
            "id": facility.id,
            "name": facility.name,
            "facility_type": "Educational Inst",
            "address": facility.address,
            "location": {"latitude": facility.location.tuple[1], "longitude": facility.location.tuple[0],},
            "local_body": None,
            "local_body_object": None,
            "district": facility.district.id,
            "district_object": {
                "id": facility.district.id,
                "name": facility.district.name,
                "state": facility.district.state.id,
            },
            "state": facility.state.id,
            "state_object": {"id": facility.state.id, "name": facility.state.name},
            "oxygen_capacity": facility.oxygen_capacity,
            "phone_number": facility.phone_number,
            "created_date": mock_equal,
            "modified_date": mock_equal,
        }

    def test_others_cant_update_ones_facility(self, client, user, facility):
        client.force_authenticate(user=user)
        response = client.post(
            "/api/v1/facility/bulk_upsert/",
            data=[
                {
                    "name": facility.name,
                    "district": facility.district.id,
                    "facility_type": 3,
                    "address": facility.address,
                    "capacity": [{"room_type": 1, "total_capacity": 100, "current_capacity": 48,}],
                },
            ],
        )
        assert response.status_code == 403

    def test_admins_can_update_ones_facility(self, client, user, facility):
        client.force_authenticate(user=user)
        user.is_superuser = True
        user.save()
        response = client.post(
            "/api/v1/facility/bulk_upsert/",
            data=[
                {
                    "name": facility.name,
                    "district": facility.district.id,
                    "facility_type": 3,
                    "address": facility.address,
                    "capacity": [{"room_type": 1, "total_capacity": 100, "current_capacity": 48,}],
                },
            ],
        )
        assert response.status_code == 204
