from urllib import response
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from care.facility.api.viewsets.facility import AllFacilityViewSet, FacilityViewSet
from rest_framework import status

from care.users.models import District, LocalBody, State, User, Ward



class CreateFacilityTests(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        state = State.objects.create(
            name = "Kerala"
        )
        district = District.objects.create(
            state = state,
            name = "Ernakulam"
        )
        local_body = LocalBody.objects.create(
            district = district,
            name = "Test Local Body",
            body_type = 20,
            localbody_code = "T1"
        )
        ward = Ward.objects.create(
            local_body = local_body,
            name = "Test Ward",
            number = 1
        )
        self.users = [
            User.objects.create_user(
                username='distAdmin',
                user_type = 30,
                phone_number = "+9198989898",
                gender = 1,
                age = 18,
                ward = ward,
                district = district,
                local_body = local_body,
                state = state
            ),
        ]

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