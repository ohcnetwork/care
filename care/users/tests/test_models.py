from datetime import date

from django.test import TestCase

from care.users.models import District, LocalBody, Skill, State, User


class SkillModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        """
        Initialise test data for all other methods
        """
        cls.skill = Skill.objects.create(
            name="ghatak", description="corona virus specialist"
        )

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

    def test_object_name(self):
        """Test that the correct format is returned while printing the object"""
        district = self.district
        self.assertEqual(
            str(district),
            f"{district.name}",
        )


class LocalBodyModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        """
        Initialise test data for all other methods
        """
        state = State.objects.create(name="bihar")
        district = District.objects.create(state=state, name="nam")
        cls.local_body = LocalBody.objects.create(
            district=district, name="blabla", body_type=1
        )

    def test_object_name(self):
        """Test that the correct format is returned while printing the object"""
        local_body = self.local_body
        self.assertEqual(
            str(local_body),
            f"{local_body.name} ({local_body.body_type})",
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
            username="test",
            user_type=5,
            district=district,
            phone_number=8_888_888_888,
            gender=1,
            date_of_birth=date(2005, 1, 1),
        )
