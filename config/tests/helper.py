"""Use this module for tests in all other modules"""
from django.contrib.gis.geos import Point

from care.facility.models import Disease, Facility, PatientRegistration
from care.users.models import District, State, User

# will be fixed later


class TestHelper:
    """Initialize objects that will be useful for all other tests"""

    @classmethod
    def setup_data(cls):
        """Initialize the data objects to be used for other function"""
        state = State.objects.create(name="KL")
        cls.district = District.objects.create(name="Kannur", state=state)
        cls.user = User.objects.create(
            user_type=10,
            district=cls.district,
            phone_number="8887776665",
            gender=2,
            age=30,
            email="foo@foobar.com",
            username="user",
        )
        cls.user.set_password("bar")
        cls.user.save()

        cls.user_creds = {
            "username": "user",
            "password": "bar",
        }

        cls.user_data = {
            "user_type": 10,
            "district": cls.district,
            "phone_number": "8887776665",
            "gender": 2,
            "age": 30,
            "email": "foo@foobar.com",
            "username": "user",
            "password": "bar",
        }

        # this is weird but it is what it is, this data will be used when using the request API
        cls.user_data_client = cls.user_data.copy()
        cls.user_data_client["user_type"] = "Staff"
        cls.user_data_client["district"] = cls.district.id

        cls.facility_data = {
            "name": "Foo",
            "district": cls.district.id,
            "facility_type": 1,
            "address": "8/88, 1st Cross, 1st Main, Boo Layout",
            "location": {"latitude": 49.878248, "longitude": 24.452545},
            "oxygen_capacity": 10,
            "phone_number": "9998887776",
        }

        cls.patient_data = {
            "name": "Foo",
            "age": 40,
            "gender": 1,
            "phone_number": "9998887776",
            "contact_with_carrier": True,
            "medical_history": [{"disease": 1, "details": "Quite bad"}],
        }

        cls.patient = PatientRegistration.objects.create(
            name="Bar", age=31, gender=2, phone_number="7776665554", contact_with_carrier=False,
        )
        cls.patient_data["id"] = cls.patient.id

        cls.disease = Disease.objects.create(disease=1, details="Quite bad", patient=cls.patient)

        cls.facility = Facility.objects.create(
            name="Foo",
            district=cls.district,
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


class EverythingEquals:
    def __eq__(self, other):
        return True


mock_equal = EverythingEquals()


def assert_equal_dicts(d1, d2, ignore_keys=[]):
    def check_equal():
        ignored = set(ignore_keys)
        for k1, v1 in d1.items():
            if k1 not in ignored and (k1 not in d2 or d2[k1] != v1):
                print(k1, v1, d2[k1])
                return False
        for k2, v2 in d2.items():
            if k2 not in ignored and k2 not in d1:
                print(k2, v2)
                return False
        return True

    return check_equal()
