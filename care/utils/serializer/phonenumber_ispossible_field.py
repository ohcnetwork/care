import phonenumbers
from django.utils.translation import gettext_lazy as _
from phonenumber_field.phonenumber import to_python
from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class PhoneNumberIsPossibleField(serializers.CharField):
    default_error_messages = {"invalid": _("Enter a valid phone number.")}

    def to_internal_value(self, data):
        if self.allow_blank and (not data):
            return None
        phone_number = to_python(data)
        if phone_number and not phonenumbers.is_possible_number(phone_number):
            # attempting to check if this is a possible Indian number
            phone_number = to_python(data, region="IN")
            if phone_number and not phonenumbers.is_possible_number(phone_number):
                raise ValidationError(self.error_messages["invalid"])
        return phone_number
