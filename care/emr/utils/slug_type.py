import re
from typing import Annotated

from pydantic import AfterValidator, Field


def slug_validator(value: str) -> str:
    """Validate slug format and length"""
    if not isinstance(value, str):
        raise ValueError("Slug must be a string")

    if not value:
        raise ValueError("Slug cannot be empty")

    pattern = r"^[-\w]+$"
    if not re.match(pattern, value, re.ASCII):
        raise ValueError(
            "Slug must contain only URL-safe characters (lowercase letters, numbers, hyphens, and underscores). "
            "It must start and end with alphanumeric characters."
        )

    return value


# Define reusable slug types with different lengths
SlugType = Annotated[
    str, Field(min_length=5, max_length=25), AfterValidator(slug_validator)
]
