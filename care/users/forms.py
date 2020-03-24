from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout
from django.contrib.auth import forms, get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

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

    # Browsers seem to ignore autocomplete="off" attribute.
    # Hence, setting value to a random string as suggested in https://stackoverflow.com/a/49053259
    autocomplete_value = "turnOff"

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
            "district": "Pick Your District",
            "phone_number": "Enter Your 10 Digit Mobile Number",
            "gender": "Pick Your Gender",
            "age": "Enter Your Age",
            "skill": "Pick Your Role",
            "username": "Enter A Username",
        }

    def __init__(self, *args, **kwargs):
        super(CustomSignupForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field('username', autocomplete=self.autocomplete_value),
            Field('first_name'),
            Field('last_name'),
            Field('email', autocomplete=self.autocomplete_value),
            Field('district', autocomplete=self.autocomplete_value),
            Field('phone_number'),
            Field('gender', autocomplete=self.autocomplete_value),
            Field('age', autocomplete=self.autocomplete_value),
            Field('skill', autocomplete=self.autocomplete_value),
            Field('password1', autocomplete=self.autocomplete_value),
            Field('password2', autocomplete=self.autocomplete_value),
        )


class AuthenticationForm(forms.AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(AuthenticationForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('username', placeholder=" Username", css_class=""),
            Field('password', placeholder="Password", css_class=""),
        )
