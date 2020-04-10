import datetime

from django.contrib.gis.geos import Point
from rest_framework import status

from care.facility.models import Facility, FacilityPatientStatsHistory
from care.utils.tests.test_base import TestBase
from config.tests.helper import mock_equal


class TestPatientStatsHistory(TestBase):
    """Test patient statistics history APIs"""

    @classmethod
    def setUpClass(cls):
        """
        Runs once per class
            - Initialize the attributes useful for class methods
        """
        super(TestPatientStatsHistory, cls).setUpClass()
        cls.stats_data = {
            "num_patients_visited": 1,
            "num_patients_home_quarantine": 2,
            "num_patients_isolation": 3,
            "num_patient_referred": 4,
        }

    def get_base_url(self) -> str:
        return f"/api/v1/facility/{self.facility.id}/patient_stats"

    def get_list_representation(self, facility_data) -> dict:

        if not facility_data:
            facility_data = self.facility_data

        location = facility_data.pop("location", None)

        return {
            **facility_data,
            "location": Point(location["latitude"], location["longitude"]),
        }

    def get_detail_representation(self, stats_data, facility=Facility) -> dict:
        if not stats_data:
            stats_data = self.stats_data

        return {
            "id": mock_equal,
            "facility": facility.id,
            "entry_date": mock_equal,
            "created_date": mock_equal,
            "modified_date": mock_equal,
            **stats_data,
        }

    def test_login_required(self):
        """Test unauthenticated users aren't allowed access"""
        self.client.logout()
        response = self.client.post(self.get_url(), {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_patient_history(self):
        """Test patient history can be created"""
        facility = self.facility
        stats_data = self.stats_data

        # test for auto-generate date
        response = self.client.post(self.get_url(), stats_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertDictEqual(
            response.json(), self.get_detail_representation(stats_data, facility=facility),
        )

        # test for provided date
        entry_date = datetime.datetime(2020, 4, 1).date()
        response = self.client.post(self.get_url(), {"entry_date": entry_date, **stats_data},)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        old_response_json = response.json()
        self.assertDictEqual(
            old_response_json, self.get_detail_representation(stats_data, facility=facility),
        )

        # test for override of info
        entry_date = datetime.datetime(2020, 4, 1).date()
        new_stats_data = {k: v + 2 for k, v in stats_data.items()}
        response = self.client.post(self.get_url(), {"entry_date": entry_date, **new_stats_data})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertDictEqual(
            response.json(), self.get_detail_representation(new_stats_data, facility=facility),
        )

    def test_patient_history_list(self):
        """Test patient history list is displayed with the correct data"""
        stats_data = self.stats_data
        facility = self.facility
        facility_data = self.facility_data.copy()

        facility_data["district"] = self.district
        facility_2 = self.create_facility(district=self.district, name="Facility 2")

        FacilityPatientStatsHistory.objects.create(
            facility=facility, entry_date=datetime.date(2020, 4, 1), **stats_data
        )
        FacilityPatientStatsHistory.objects.create(
            facility=facility, entry_date=datetime.date(2020, 4, 2), **stats_data
        )
        FacilityPatientStatsHistory.objects.create(
            facility=facility_2, entry_date=datetime.date(2020, 4, 2), **stats_data
        )

        response = self.client.get(self.get_url())
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

        response = self.client.get(self.get_url(entry_id=obj.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve(self):
        """Test patient history data is returned as expected"""
        stats_data = self.stats_data
        facility = self.facility

        obj = FacilityPatientStatsHistory.objects.create(
            facility=facility, entry_date=datetime.date(2020, 4, 1), **stats_data
        )

        response = self.client.get(self.get_url(entry_id=obj.id), format="json")
        self.assertDictEqual(
            response.json(), self.get_detail_representation(stats_data, facility=facility),
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

        response = self.client.delete(self.get_url(entry_id=obj.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            FacilityPatientStatsHistory.objects.filter(facility=facility).count(), count - 1,
        )

    def test_update_should_not_be_allowed(self):
        """Test users can't update patient history"""
        response = self.client.put(self.get_url(), {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_partial_update_should_not_be_allowed(self):
        """Test partial update is also not allowed"""
        response = self.client.patch(self.get_url(), {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
