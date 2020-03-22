from django.contrib.auth import forms, get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field


User = get_user_model()


class UserChangeForm(forms.UserChangeForm):
    class Meta(forms.UserChangeForm.Meta):
        model = User


class UserCreationForm(forms.UserCreationForm):

    error_message = forms.UserCreationForm.error_messages.update(
        {"duplicate_username": _("This username has already been taken.")}
    )

    class Meta(forms.UserCreationForm.Meta):
        model = User

    def clean_username(self):
        username = self.cleaned_data["username"]

        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username

        raise ValidationError(self.error_messages["duplicate_username"])


class CustomSignupForm(forms.UserCreationForm):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "district",
            "phone_number",
            "gender",
            "age",
            "skill",
            "username",
            "password1",
            "password2",
        )
        labels = {
        "first_name": "Enter Your First Name*",
        "last_name": "Enter Your Last Name",
        "email": "Enter Your Email Address",
        "district":"Pick Your District",
        "phone_number": "Enter Your 10 Digit Mobile Number",
        "gender":"Pick Your Gender",
        "age":"Enter Your Age",
        "skill":"Pick Your Role",
        "username":"Enter A Username",   
        }

    def __init__(self, *args, **kwargs):
        super(CustomSignupForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('username',placeholder= "Desired Username", css_class=""),
            Field('first_name',placeholder= "Your first name", css_class=""),
            Field('last_name',placeholder= "Your last name", css_class=""),
            Field('email',placeholder="Your Email Address", css_class=""),
            Field('district', css_class=""),
            Field('phone_number',placeholder="Your 10 Digit Mobile Number", css_class="'"),
            Field('gender', css_class=""),
            Field('age',placeholder= "Your age in numbers", css_class=""),
            Field('skill', css_class=""),
            Field('password1',placeholder= "Password Confirmation", css_class=""),
        Field('password2',placeholder= "Password", css_class=""),
        )


class AuthenticationForm(forms.AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(AuthenticationForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('username',placeholder= " Username", css_class=""),
            Field('password',placeholder= "Password", css_class=""),
        )
