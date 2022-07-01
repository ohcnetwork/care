from django.test import TestCase
from rest_framework.test import force_authenticate
from care.facility.api.viewsets.facility import AllFacilityViewSet, FacilityViewSet
from rest_framework import status

from care.facility.tests.mixins import TestClassMixin

class CreateFacilityTests(TestClassMixin, TestCase):

    def test_all_listing(self):
        request = self.factory.get('/api/v1/getallfacilitiess/')
        view = AllFacilityViewSet.as_view({'get': 'list'})
        response = view(request)
        self.assertIs(response.status_code, status.HTTP_200_OK)

    def test_listing(self):
        request = self.factory.get('/api/v1/facility/')
        view = FacilityViewSet.as_view({'get': 'list'})
        force_authenticate(request, user=self.users[0])
        response = view(request)
        print(response.data)
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
        }
        request = self.factory.post('/api/v1/facility/', sample_data, format='json')
        view = FacilityViewSet.as_view({'post': 'create'})
        force_authenticate(request, user=self.users[0])
        response = view(request)
        self.assertIs(response.status_code, status.HTTP_201_CREATED)