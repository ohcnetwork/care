from django.test import TestCase
from care.facility.api.viewsets.facility import AllFacilityViewSet, FacilityViewSet
from rest_framework import status

from care.facility.tests.mixins import TestClassMixin

class FacilityTests(TestClassMixin, TestCase):

    def test_all_listing(self):
        response = self.new_request(
            ('/api/v1/getallfacilitiess/',), 
            {'get' : 'list'}, 
            AllFacilityViewSet
        )
        self.assertIs(response.status_code, status.HTTP_200_OK)

    def test_listing(self):
        response = self.new_request(
            ('/api/v1/facility/',), 
            {'get' : 'list'}, 
            FacilityViewSet,
            self.users[0]
        )
        self.assertIs(response.status_code, status.HTTP_200_OK)

    def test_create(self):
        user = self.users[0]
        sample_data = {
            "name": "Hospital X",
            "ward": user.ward.pk,
            "local_body": user.local_body.pk,
            "district": user.district.pk,
            "state": user.state.pk,
            "facility_type": "Educational Inst",
            "address": "Nearby",
            "pincode": 390024,
            "features" : []
        }
        response = self.new_request(
            ('/api/v1/facility/', sample_data, 'json'), 
            {'post': 'create'},
            FacilityViewSet,
            user
        )
        fac_id = response.data['id']
        self.assertIs(response.status_code, status.HTTP_201_CREATED)

        retrieve_response = self.new_request(
            (f'/api/v1/facility/{fac_id}',), 
            {'get': 'retrieve'},
            FacilityViewSet,
            user,
            {'external_id' : fac_id}
        )

        self.assertIs(retrieve_response.status_code, status.HTTP_200_OK)

    def test_no_auth(self):
        response = self.new_request(
            ('/api/v1/facility/',), 
            {'get' : 'list'}, 
            FacilityViewSet,
        )
        self.assertIs(response.status_code, status.HTTP_403_FORBIDDEN)

        sample_data = {}
        create_response = self.new_request(
            ('/api/v1/facility/', sample_data, 'json'), 
            {'post': 'create'},
            FacilityViewSet,
        )
        self.assertIs(create_response.status_code, status.HTTP_403_FORBIDDEN)