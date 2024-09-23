from rest_framework import serializers


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


class MultipleChoiceField(serializers.MultipleChoiceField):
    def to_representation(self, value):
        return super().to_representation(value)

    def to_internal_value(self, data):
        return super().to_internal_value(data)
