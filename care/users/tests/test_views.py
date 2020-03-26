from django.test import TestCase
from django.urls import reverse


class HomeView(TestCase):
    """
    For HomeView, test
        - url is accessible by name
        - correct template is used
    """

    def test_url_name_for_home_view(self):
        """Test whether home page is accessible"""
        url_home = reverse("home")
        response = self.client.get(url_home)
        self.assertEqual(response.status_code, 200)

    # This is not required, moving to a react frontend

    # def test_correct_template_used_for_home_view(self):
    #     """Test whether correct template is used"""
    #     url_home = reverse("home")
    #     response = self.client.get(url_home)
    #     self.assertTemplateUsed(response, template_name="pages/home.html")


class SignupViewTest(TestCase):
    """
    For SignupView, test
        - url name is accessible for
            - volunteer
            - doctor
            - staff
    """

    def __init__(self, *args, **kwargs):
        super(SignupViewTest, self).__init__(*args, **kwargs)
        self.username = "doctor"
        self.user_type = 5
        self.first_name = "Jach"
        self.last_name = "Karta"
        self.email = "a@a.com"
        self.district = 1
        self.phone_number = 8_888_888_888
        self.gender = 2
        self.age = 22
        self.password = "user123#"

    @classmethod
    def setUpTestData(cls):
        """
        Initialize the form data
            - create a user
        """
        cls.data = {
            "username": "tester",
            "first_name": "Jach",
            "last_name": "Karta",
            "email": "a@a.com",
            "district": 1,
            "phone_number": 8_888_888_888,
            "gender": 1,
            "age": 22,
            "password1": "user123#",
            "password2": "user123#",
        }

    def test_url_name_for_signin_view_volunteer(self):
        """Test whether home page is accessible for volunteer"""
        url_signup = reverse("users:signup-volunteer")
        response = self.client.get(url_signup)
        self.assertEqual(response.status_code, 200)

    def test_url_name_for_signin_view_doctor(self):
        """Test whether home page is accessible for doctor"""
        url_signup = reverse("users:signup-doctor")
        response = self.client.get(url_signup)
        self.assertEqual(response.status_code, 200)

    def test_url_name_for_signin_view_staff(self):
        """Test whether home page is accessible for staff"""
        url_signup = reverse("users:signup-staff")
        response = self.client.get(url_signup)
        self.assertEqual(response.status_code, 200)

    # This is not required, moving to a react frontend

    # def test_correct_template_used_for_signin_view(self):
    #     """Test whether correct template is used"""
    #     url_signup = reverse("users:signup-doctor")
    #     response = self.client.get(url_signup)
    #     self.assertTemplateUsed(response, template_name="users/signup.html")

    def test_username_integrity(self):
        """
        Test invalidation for use of 1 username by more than 1 accounts,\
        raising of appropriate validation error
        """
        url_signup = reverse("users:signup-staff")
        # create first_user
        response = self.client.post(url_signup, data=self.data)
        response = self.client.post(url_signup, data=self.data)
        # Test invalidation of form
        form = response.content["form"]
        self.assertEqual(form.is_valid(), False)
        # Test if validation error is raised
        self.assertEqual(form.has_error("duplicate_username", code="invalid"), True)

    def test_redirect_on_successful_registration(self):
        """Test redirect to home page on successful registration"""
        data = self.data
        # change username
        response = self.client.post(reverse("users:signup-doctor"), data=data)
        self.assertRedirects(response, expected_url=reverse("home"))
