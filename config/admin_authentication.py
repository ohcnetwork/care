from django.contrib.auth.forms import AuthenticationForm
from django.forms import ValidationError


class CustomLoginForm(AuthenticationForm):

    # overriding clean method to change default authentication behaviour
    def clean(self):
        print("bleh")
        cleaned_data = super(CustomLoginForm, self).clean()
        print("bleh")
