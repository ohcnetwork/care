from enum import Enum


class EnumChoices:
    """
    Creates a choice field using Enum

    Params:
        name: str
            the name given to the enum choices
        choices: dict
            The dictionary used for creating choices

    example:
    >>> gender_choices = EnumChoices(choices={'Male':1, 'Female': 2, 'Non-Binary': 3})

    # For using the values inside a model, use
    >>> gender_choices.list_tuple_choices()
    [('Male', 1), ('Female', 2), ('Non-binary', 3)]

    # For accessing a choice
    >>> gender_choices.choice.Female
    <choices.Female: 2>

    # For accessing a value
    >>> gender_choices.choices.Female.value
    2

    # This also works
    >>> gender_choices.choices['Female']
    <choices.Female: 2>
    >>> gender_choices.choices['Female'].value
    2

    """

    def __init__(self, name="choices", choices=None):
        """Create enum choices for list of tuples passed"""
        if not choices:
            raise ValueError("No argument passed")
        if not isinstance(choices, dict):
            raise TypeError(f"Invalid instance of choices passed, {type(choices)} is not a {dict}")
        self.choices = Enum(name, choices)

    def list_tuple_choices(self):
        """
        Returns a list of choices tuples, useful for passing the choices to models
        """
        return [(choice.value, choice.name) for choice in self.choices]
