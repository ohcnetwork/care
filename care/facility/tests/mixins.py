from django.test import TestCase
from rest_framework.test import force_authenticate
from rest_framework.test import APIRequestFactory
from care.users.models import District, LocalBody, State, User, Ward

class TestClassMixin(TestCase):
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
                phone_number = "+919898989898",
                gender = 1,
                age = 18,
                ward = ward,
                district = district,
                local_body = local_body,
                state = state,
                verified = True
            ),
        ]

    def new_request(self, params, method, viewset, authenticate = False, pk = {}):
        
        request_methods = {
            "get" :  self.factory.get,
            "post" : self.factory.post,
            "patch" : self.factory.patch,
            "put" : self.factory.put,
            "delete" : self.factory.delete
        }

        method_type = list(method.keys())[0]
        request = request_methods[method_type](*params)
        view = viewset.as_view(method)
        authenticate != False and force_authenticate(request, user=authenticate) 
        return view(request, **pk)