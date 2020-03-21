from django.contrib.auth import forms, get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, ButtonHolder, Submit, Fieldset
from django.contrib.auth.forms import AuthenticationForm


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


from django.contrib.auth.forms import UserCreationForm


class CustomSignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "district",
            "phone_number",
            "gender",
            "age",
            "skill",
            "password1",
            "password2",
        )
        labels = {
        "first_name": "First Name",
        "last_name": "Last Name",
        "email": "Email Address",
        "phone_number": "10 Digit Mobile Number",
        "password2": "Password Confirmation",
        }

    def __init__(self, *args, **kwargs):
        super(CustomSignupForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('username',placeholder= "Desired Username", css_class="form-input block w-full"),
            Field('first_name',placeholder= "Your first name", css_class="form-input block w-full"),
            Field('last_name',placeholder= "Your last name", css_class="form-input block w-full"),
            Field('email',placeholder="Your Email Address", css_class="form-input block w-full"),
            Field('district', css_class="form-select block w-full"),
            Field('phone_number',placeholder="Your 10 Digit Mobile Number", css_class="form-input block w-full"),
            Field('gender', css_class="form-select block"),
            Field('age',placeholder= "Your age in numbers", css_class="form-input block w-full"),
            Field('skill', css_class="form-select block"),
            Field('password1',placeholder= "Password Confirmation", css_class="form-input block w-full"),
        Field('password2',placeholder= "Password", css_class="form-input block w-full"),
        )


class AuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(AuthenticationForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('username',placeholder= " Username", css_class="form-input appearance-none block w-full text-sm bg-white border border-gray-400 rounded py-3 px-4 mt-2 leading-tight focus:outline-none focus:bg-white focus:border-gray-500"),
            Field('password',placeholder= "Password", css_class="appearance-none block w-full text-sm bg-white border border-gray-400 rounded py-3 px-4 mt-2 leading-tight focus:outline-none focus:bg-white focus:border-gray-500"),
        )
