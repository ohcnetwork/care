"""Use this module for tests in all other modules"""
# from care.users.models import User

# will be fixed later

# class TestHelper:
#     """Initialize objects that will be useful for all other tests"""

#     def setup_data(self, *args, **kwargs):
#         self.data = {
#             "user_type": 5,
#             "email": "some.email@somedomain.com",
#             "phone_number": "5554446667",
#             "age": 30,
#             "gender": 2,
#             "district": 11,
#             "username": "user",
#             "password": "bar",
#         }
#         self.user = User.objects.create_user(
#             user_type=5,
#             district=13,
#             phone_number="8887776665",
#             gender=1,
#             age=30,
#             email="foo@foobar.com",
#             username="user",
#             password="user123#",
#         )


class EverythingEquals:
    def __eq__(self, other):
        return True


mock_equal = EverythingEquals()


def assert_equal_dicts(d1, d2, ignore_keys=[]):
    ignored = set(ignore_keys)
    for k1, v1 in d1.iteritems():
        if k1 not in ignored and (k1 not in d2 or d2[k1] != v1):
            return False
    for k2, v2 in d2.iteritems():
        if k2 not in ignored and k2 not in d1:
            return False
    return True
