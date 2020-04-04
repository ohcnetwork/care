"""Use this module for tests in only users api"""
from care.users.models import District, State, User

# will be fixed later


class TestHelper:
    """Initialize objects that will be useful for all other tests"""

    @classmethod
    def setup_data(cls):
        """Initialize the data objects to be used for other function"""
        cls.state = State.objects.create(name="KL")
        cls.district = District.objects.create(name="Kannur", state=cls.state)
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
            "phone_number": "8887776665",
            "gender": 2,
            "age": 30,
            "email": "foo@foobar.com",
            "username": "user",
            "password": "bar",
        }

        # # this is weird but it is what it is, this data will be used when using the request API
        cls.user_data_client = cls.user_data.copy()
        cls.user_data_client["user_type"] = "Staff"


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
