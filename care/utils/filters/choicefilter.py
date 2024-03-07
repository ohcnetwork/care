from django_filters.filters import CharFilter


def inverse_choices(choices):
    output = {}
    for choice in choices:
        output[choice[1]] = choice[0]
    return output


def inverse_choices_class(choices_class):
    output = {}
    for choice in choices_class:
        output[choice.name] = choice.value
    return output


class CareChoiceFilter(CharFilter):
    def __init__(self, *args, **kwargs):
        if "choice_dict" in kwargs:
            self.choice_dict = kwargs.pop("choice_dict")
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if len(value) > 0:
            value = self.choice_dict.get(value)
        return super().filter(qs, value)
