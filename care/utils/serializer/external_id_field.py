import uuid

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.fields import empty
from rest_framework.serializers import Field, ValidationError


class UUIDValidator:
    def __call__(self, value):
        try:
            return uuid.UUID(value)
        except ValueError:
            raise ValidationError("invalid uuid") from None


class ExternalIdSerializerField(Field):
    def __init__(self, queryset=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = queryset

    def get_validators(self):
        validators = super().get_validators()
        validators += [UUIDValidator()]
        return validators

    def to_internal_value(self, data):
        return data

    def to_representation(self, value):
        return value.external_id if value else None

    def run_validation(self, data=empty):
        value = super().run_validation(data)
        if value:
            try:
                value = self.queryset.get(external_id=value)
            except ObjectDoesNotExist:
                raise ValidationError("object with this id not found") from None
        return value
