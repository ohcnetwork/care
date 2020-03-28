"""Use this modile for tests in all other modules"""
from care.users.models import User


class TestHelper:
    """Initialize objects that will be useful for all other tests"""

    def __init__(self, *args, **kwargs):
        breakpoint()
        self.super_user = User.objects.create_superuser(
            user_type=5,
            district=13,
            phone_number="8887776665",
            gender=1,
            age=30,
            email="foo@foobar.com",
            username="supeuser",
            password="user123#",
        )
