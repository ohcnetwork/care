import datetime

from django.contrib.gis.geos import Point
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import Facility, FacilityPatientStatsHistory
from care.users.models import User
from config.tests.helper import mock_equal


class TestPatientStatsHistory(APITestCase):
    """Test patient statistics history APIs"""

    @classmethod
    def setUpTestData(cls):
        cls.facility_data = {
            "name": "Foo",
            "district": 13,
            "facility_type": 1,
            "address": "8/88, 1st Cross, 1st Main, Boo Layout",
            "location": {"latitude": 49.878248, "longitude": 24.452545},
            "oxygen_capacity": 10,
            "phone_number": "9998887776",
        }
        cls.facility = Facility.objects.create(
            name="Foo",
            district=13,
            facility_type=1,
            address="8/88, 1st Cross, 1st Main, Boo Layout",
            location=Point(24.452545, 49.878248),
            oxygen_capacity=10,
            phone_number="9998887776",
        )
        cls.stats_data = {
            "num_patients_visited": 1,
            "num_patients_home_quarantine": 2,
            "num_patients_isolation": 3,
            "num_patient_referred": 4,
        }
        cls.user_data = {
            "user_type": 5,
            "email": "some.email@somedomain.com",
            "phone_number": "5554446667",
            "age": 30,
            "gender": 2,
            "district": 11,
            "username": "user_1",
            "password": "bar",
        }
        cls.user = User.objects.create_user(**cls.user_data)

    def setUp(self):
        """
        Run before every class method
            - log in a user
        """
        self.client.login(username=self.user_data["username"], password=self.user_data["password"])

    @staticmethod
    def get_url(facility_id, entry_id=None):
        """
        Returns url for the parameters passed

        Return
            str

        Params
            facility_id: int
                The facility id to be used for forming the url for the API

            entry_id: int
                The value to be used for constructing detail url if required
                Default: None

        """
        url = f"/api/v1/facility/{facility_id}/patient_stats/"
        if entry_id:
            url = f"{url}{entry_id}/"
        return url

    def test_login_required(self):
        """Test unauthenticated users aren't allowed access"""
        self.client.logout()
        response = self.client.post(self.get_url(self.facility.id), {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_patient_history(self):
        """Test patient history can be created"""
        facility = self.facility
        stats_data = self.stats_data

        # test for auto-generate date
        response = self.client.post(self.get_url(facility.id), stats_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertDictEqual(
            response.json(),
            {
                "id": mock_equal,
                "facility": facility.id,
                "entry_date": datetime.datetime.today().strftime("%Y-%m-%d"),
                "created_date": mock_equal,
                "modified_date": mock_equal,
                **stats_data,
            },
        )

        # test for provided date
        entry_date = datetime.datetime(2020, 4, 1).date()
        response = self.client.post(self.get_url(facility.id), {"entry_date": entry_date, **stats_data})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertDictEqual(
            response.json(),
            {
                "id": mock_equal,
                "facility": facility.id,
                "entry_date": entry_date.strftime("%Y-%m-%d"),
                "created_date": mock_equal,
                "modified_date": mock_equal,
                **stats_data,
            },
        )
        old_response_json = response.json()

        # test for override of info
        entry_date = datetime.datetime(2020, 4, 1).date()
        new_stats_data = {k: v + 2 for k, v in stats_data.items()}
        response = self.client.post(self.get_url(facility.id), {"entry_date": entry_date, **new_stats_data})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertDictEqual(
            response.json(),
            {
                "id": old_response_json["id"],
                "facility": facility.id,
                "entry_date": entry_date.strftime("%Y-%m-%d"),
                "created_date": mock_equal,
                "modified_date": mock_equal,
                **new_stats_data,
            },
        )

    def test_patient_history_list(self):
        """Test patient history list is displayed with the correct data"""
        stats_data = self.stats_data
        facility = self.facility
        facility_data = self.facility_data

        location = facility_data.pop("location", None)
        facility_2 = Facility.objects.create(
            **{**facility_data, "location": Point(location["latitude"], location["longitude"]),}
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

        response = self.client.get(self.get_url(facility.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(
            response.json(),
            {
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
            },
        )

    def test_retrieve_url_by_location(self):
        """Test patient history url is accessible"""
        stats_data = self.stats_data
        facility = self.facility

        obj = FacilityPatientStatsHistory.objects.create(
            facility=facility, entry_date=datetime.date(2020, 4, 1), **stats_data
        )

        response = self.client.get(self.get_url(facility.id, entry_id=obj.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve(self):
        """Test patient history data is returned as expected"""
        stats_data = self.stats_data
        facility = self.facility

        obj = FacilityPatientStatsHistory.objects.create(
            facility=facility, entry_date=datetime.date(2020, 4, 1), **stats_data
        )

        response = self.client.get(self.get_url(facility.id, entry_id=obj.id))
        self.assertDictEqual(
            response.json(),
            {
                "id": obj.id,
                "facility": facility.id,
                "entry_date": datetime.date(2020, 4, 1).strftime("%Y-%m-%d"),
                "created_date": mock_equal,
                "modified_date": mock_equal,
                **stats_data,
            },
        )

    def test_destroy_patient_history(self):
        """
        Test patient history can be deleted
            - test status code for the request
            - test data count in the database decreases by 1
        """
        facility = self.facility
        obj = FacilityPatientStatsHistory.objects.create(
            facility=facility, entry_date=datetime.date(2020, 4, 1), **self.stats_data
        )
        count = FacilityPatientStatsHistory.objects.filter(facility=facility).count()

        response = self.client.delete(self.get_url(facility.id, entry_id=obj.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            FacilityPatientStatsHistory.objects.filter(facility=facility).count(), count - 1,
        )

    def test_update_should_not_be_allowed(self):
        """Test users can't update patient history"""
        response = self.client.put(self.get_url(self.facility.id), {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_partial_update_should_not_be_allowed(self):
        """Test partial update is also not allowed"""
        response = self.client.patch(self.get_url(self.facility.id), {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
