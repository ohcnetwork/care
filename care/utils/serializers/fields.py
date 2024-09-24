import uuid

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.fields import empty


class UUIDValidator:
    def __call__(self, value):
        try:
            return uuid.UUID(value)
        except ValueError as e:
            msg = "invalid uuid"
            raise serializers.ValidationError(msg) from e


class ExternalIdSerializerField(serializers.UUIDField):
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
            except ObjectDoesNotExist as e:
                msg = "object with this id not found"
                raise serializers.ValidationError(msg) from e
        return value


class ChoiceField(serializers.ChoiceField):
    def to_representation(self, obj):
        try:
            return self._choices[obj]
        except KeyError:
            key_type = type(next(iter(self.choices.keys())))
            key = key_type(obj)
            return self._choices[key]

    def to_internal_value(self, data):
        if isinstance(data, str) and data not in self.choice_strings_to_values:
            choice_name_map = {v: k for k, v in self._choices.items()}
            data = choice_name_map.get(data)
        return super().to_internal_value(data)
