import datetime

import pytest
from django.contrib.gis.geos import Point
from rest_framework import status

from care.facility.models import District, Facility, FacilityPatientStatsHistory, State
from config.tests.helper import mock_equal


@pytest.fixture()
def facility():
    s = State.objects.create(name="KL")
    d = District.objects.create(name="Kannur", state=s)
    return Facility.objects.create(
        name="Foo",
        district=d,
        facility_type=1,
        address="8/88, 1st Cross, 1st Main, Boo Layout",
        location=Point(24.452545, 49.878248),
        oxygen_capacity=10,
        phone_number="9998887776",
    )


@pytest.fixture()
def stats_data():
    return {
        "num_patients_visited": 1,
        "num_patients_home_quarantine": 2,
        "num_patients_isolation": 3,
        "num_patient_referred": 4,
    }


@pytest.mark.django_db(transaction=True)
class TestPatientStatsHistory:
    @staticmethod
    def get_url(facility_id, entry_id=None):
        url = f"/api/v1/facility/{facility_id}/patient_stats/"
        if entry_id:
            url = f"{url}{entry_id}/"
        return url

    def test_login_required(self, client, facility):
        response = client.post(self.get_url(facility.id), {})
        assert response.status_code == 403

    def test_create(self, client, user, facility, stats_data):
        client.force_authenticate(user=user)

        # test for auto-generate date
        response = client.post(self.get_url(facility.id), stats_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json() == {
            "id": mock_equal,
            "facility": facility.id,
            "entry_date": datetime.datetime.today().strftime("%Y-%m-%d"),
            "created_date": mock_equal,
            "modified_date": mock_equal,
            **stats_data,
        }

        # test for provided date
        entry_date = datetime.datetime(2020, 4, 1).date()
        response = client.post(self.get_url(facility.id), {"entry_date": entry_date, **stats_data})
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json() == {
            "id": mock_equal,
            "facility": facility.id,
            "entry_date": entry_date.strftime("%Y-%m-%d"),
            "created_date": mock_equal,
            "modified_date": mock_equal,
            **stats_data,
        }
        old_response_json = response.json()

        # test for override of info
        entry_date = datetime.datetime(2020, 4, 1).date()
        new_stats_data = {k: v + 2 for k, v in stats_data.items()}
        response = client.post(self.get_url(facility.id), {"entry_date": entry_date, **new_stats_data})
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json() == {
            "id": old_response_json["id"],
            "facility": facility.id,
            "entry_date": entry_date.strftime("%Y-%m-%d"),
            "created_date": mock_equal,
            "modified_date": mock_equal,
            **new_stats_data,
        }

    def test_list(self, client, user, facility, facility_data, stats_data):
        client.force_authenticate(user=user)
        location = facility_data.pop("location", None)
        facility_data.pop("district")
        facility_2 = Facility.objects.create(
            **{**facility_data, "location": Point(location["latitude"], location["longitude"])}
        )

        FacilityPatientStatsHistory.objects.create(
            facility=facility, entry_date=datetime.date(2020, 4, 1), **stats_data
        )
        FacilityPatientStatsHistory.objects.create(
            facility=facility, entry_date=datetime.date(2020, 4, 2), **stats_data
        )
        FacilityPatientStatsHistory.objects.create(
            facility=facility_2, entry_date=datetime.date(2020, 4, 2), **stats_data
        )

        response = client.get(self.get_url(facility.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": mock_equal,
                    "facility": facility.id,
                    "entry_date": datetime.date(2020, 4, 2).strftime("%Y-%m-%d"),
                    "created_date": mock_equal,
                    "modified_date": mock_equal,
                    **stats_data,
                },
                {
                    "id": mock_equal,
                    "facility": facility.id,
                    "entry_date": datetime.date(2020, 4, 1).strftime("%Y-%m-%d"),
                    "created_date": mock_equal,
                    "modified_date": mock_equal,
                    **stats_data,
                },
            ],
        }

    def test_retrieve(self, client, user, facility, stats_data):
        client.force_authenticate(user=user)
        obj = FacilityPatientStatsHistory.objects.create(
            facility=facility, entry_date=datetime.date(2020, 4, 1), **stats_data
        )

        response = client.get(self.get_url(facility.id, entry_id=obj.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "id": obj.id,
            "facility": facility.id,
            "entry_date": datetime.date(2020, 4, 1).strftime("%Y-%m-%d"),
            "created_date": mock_equal,
            "modified_date": mock_equal,
            **stats_data,
        }

    def test_destroy(self, client, user, facility, stats_data):
        client.force_authenticate(user=user)
        obj = FacilityPatientStatsHistory.objects.create(
            facility=facility, entry_date=datetime.date(2020, 4, 1), **stats_data
        )
        count = FacilityPatientStatsHistory.objects.filter(facility=facility).count()

        response = client.delete(self.get_url(facility.id, entry_id=obj.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert FacilityPatientStatsHistory.objects.filter(facility=facility).count() == count - 1

    def test_update_should_not_be_allowed(self, client, user, facility):
        client.force_authenticate(user=user)
        response = client.put(self.get_url(facility.id), {})
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_partial_update_should_not_be_allowed(self, client, user, facility):
        client.force_authenticate(user=user)
        response = client.patch(self.get_url(facility.id), {})
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
