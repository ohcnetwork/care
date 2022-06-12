from django.utils.translation import gettext as _
from rest_framework.utils.representation import smart_repr
from rest_framework import serializers

class notEmptyValidator:
    """
    Validator for checking whether the field has empty value or not
    """
    message = _('{field} cannot be empty')

    def __init__(self, field, message=None):
        self.field = field
        self.message = message or self.message

    def __call__(self, attrs):
        if not attrs[self.field].strip():
            message = self.message.format(field=self.field)
            raise serializers.ValidationError({self.field:message})

    def __repr__(self):
        return '<%s(field=%s)>' % (self.__class__.__name__, smart_repr(self.field))
