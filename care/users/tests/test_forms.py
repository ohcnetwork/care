from django.test import TestCase

from care.users.forms import UserCreationForm


class UserCreationFormTestCase(TestCase):
    """Test user creation form"""

    def test_user_type_choices_fails_for_wrong_values(self):
        """Try putting values apart from the allowed choices"""
        field = "user_type"

        # Test invalid integer choice
        form = UserCreationForm(data={field: 1})
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.has_error(field, code="invalid"), True)
        # Test invalid type of choice
        form = UserCreationForm(data={field: "1"})
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.has_error(field, code="invalid"), True)

    def test_user_type_choices_succeds_for_correct_values(self):
        """Try putting in the expected values"""
        field = "user_type"

        # Test invalid integer choice
        form = UserCreationForm(data={field: 5})
        self.assertEqual(form.has_error(field, code="invalid"), False)

    def test_district_type_choices_fails_for_wrong_values(self):
        """Try putting values apart from the allowed choices"""
        field = "user_type"

        # Test invalid integer choice
        form = UserCreationForm(data={field: 0})
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.has_error(field, code="invalid"), True)
        # Test invalid type of choice
        form = UserCreationForm(data={field: "0"})
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.has_error(field, code="invalid"), True)

    def test_district_type_choices_succeds_for_correct_values(self):
        """Try putting in the expected values"""
        field = "user_type"

        # Test invalid integer choice
        form = UserCreationForm(data={field: 5})
        self.assertEqual(form.has_error(field, code="invalid"), False)

    def test_gender_type_choices_fails_for_wrong_values(self):
        """Try putting values apart from the allowed choices"""
        field = "gender"

        # Test invalid integer choice
        form = UserCreationForm(data={field: 0})
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.has_error(field, code="invalid"), True)
        # Test invalid type of choice
        form = UserCreationForm(data={field: "0"})
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.has_error(field, code="invalid"), True)

    def test_gendere_type_choices_succeds_for_correct_values(self):
        """Try putting in the expected values"""
        field = "gender"

        # Test valid integer choice
        form = UserCreationForm(data={field: 1})
        self.assertEqual(form.has_error(field, code="invalid"), False)

    def test_phone_number_validator_fails_wrong_numbers(self):
        """Try putting values apart from the allowed choices"""
        field = "phone_number"

        # Test invalid length
        form = UserCreationForm(data={field: 123456789})
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.has_error(field, code="invalid"), True)
        # Test dummy mobile numbers
        form = UserCreationForm(data={field: 1234567890})
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.has_error(field, code="invalid"), True)
        # Test dummy landline numbers
        form = UserCreationForm(data={field: 1234567890})
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.has_error(field, code="invalid"), True)

    def test_min_value_age(self):
        """Test a value for age less than 1"""
        field = "age"
        form = UserCreationForm(data={field: 0})
        self.assertEqual(form.has_error(field, code="invalid"), True)

    def test_max_value_age(self):
        """Test a value for age greater than 100"""
        field = "age"
        form = UserCreationForm(data={field: 101})
        self.assertEqual(form.has_error(field, code="invalid"), True)

    def test_valid_value_age(self):
        """Try putting in the expected values"""
        field = "age"
        form = UserCreationForm(data={field: 10})
        self.assertEqual(form.has_error(field, code="invalid"), False)
