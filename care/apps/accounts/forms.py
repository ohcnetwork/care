from django.contrib.auth import forms as auth_forms, get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

User = get_user_model()


class UserChangeForm(auth_forms.UserChangeForm):

    class Meta:
        model = User
        fields = '__all__'


class UserCreationForm(auth_forms.UserCreationForm):
    error_message = auth_forms.UserCreationForm.error_messages.update(
        {'duplicate_username': _('This username has already been taken.')}
    )

    class Meta:
        model = User
        fields = ('email', 'user_type',)

    def clean_username(self):
        username = self.cleaned_data['username']

        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username
        else:
            raise ValidationError(self.error_messages['duplicate_username'])
