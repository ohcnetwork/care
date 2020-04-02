from django.test import TestCase

from care.users.models import District, LocalBody, Skill, State, User


class SkillModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        """
        Initialise test data for all other methods
        """
        cls.skill = Skill.objects.create(name="ghatak", description="corona virus specialist")

    def test_max_length_name(self):
        """Test max length for name is 255"""
        skill = self.skill
        max_length = skill._meta.get_field("name").max_length
        self.assertEqual(max_length, 255)

    def test_object_name(self):
        """Test that the name is returned while printing the object"""
        skill = self.skill
        self.assertEqual(str(skill), skill.name)


class StateModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        """
        Initialise test data for all other methods
        """
        cls.state = State.objects.create(name="kerala")

    def test_max_length_name(self):
        """Test max length for name is 255"""
        state = self.state
        max_length = state._meta.get_field("name").max_length
        self.assertEqual(max_length, 255)

    def test_object_name(self):
        """Test that the correct format is returned while printing the object"""
        state = self.state
        self.assertEqual(str(state), f"{state.name}")


class DistrictModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        """
        Initialise test data for all other methods
        """
        state = State.objects.create(name="uttar pradesh")
        cls.district = District.objects.create(state=state, name="name")

    def test_max_length_name(self):
        """Test max length for name is 255"""
        district = self.district
        max_length = district._meta.get_field("name").max_length
        self.assertEqual(max_length, 255)

    def test_object_name(self):
        """Test that the correct format is returned while printing the object"""
        district = self.district
        self.assertEqual(
            str(district), f"{district.name}",
        )


class LocalBodyModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        """
        Initialise test data for all other methods
        """
        state = State.objects.create(name="bihar")
        district = District.objects.create(state=state, name="nam")
        cls.local_body = LocalBody.objects.create(district=district, name="blabla", body_type=1)

    def test_max_length_name(self):
        """Test max length for name is 255"""
        local_body = self.local_body
        max_length = local_body._meta.get_field("name").max_length
        self.assertEqual(max_length, 255)

    def test_object_name(self):
        """Test that the correct format is returned while printing the object"""
        local_body = self.local_body
        self.assertEqual(
            str(local_body), f"{local_body.name} ({local_body.body_type})",
        )


class UserModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        """
        Initialize test data for all other methods.
        """
        state = State.objects.create(name="uttar pradesh")
        district = District.objects.create(state=state, name="name")
        cls.user = User.objects.create_user(
            username="test", user_type=5, district=district, phone_number=8_888_888_888, gender=1, age=21,
        )

    def test_max_length_phone_number(self):
        """Test maximum length for phone number is 14"""
        user = self.user
        max_length = user._meta.get_field("phone_number").max_length
        self.assertEqual(max_length, 14)

    def test_get_absolute_url(self):
        """Test whether model returns correct url for detail view of a user"""
        # This is part of django-cookie cutter and isn't used right now
        # Reference link for the slack thread:
        # https://rebuildearth.slack.com/archives/C010GQBMFJ9/p1585218577029200?thread_ts=1585218248.028800&cid=C010GQBMFJ9
        pass
        # user = self.user
        # url_absolute = reverse('users:detail', kwargs={'username': user.username})
        # response = self.client.get(url_absolute)
        # self.assertEqual(response.status_code, 200)
