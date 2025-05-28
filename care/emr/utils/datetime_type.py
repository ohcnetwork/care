from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator


def validate_timezone_aware(dt: datetime | None) -> datetime | None:
    """
    Validates that a datetime has timezone information.
    Raises ValueError if datetime is naive.
    Returns None if input is None.
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        raise ValueError("Datetime must be timezone aware")

    return dt


StrictTZAwareDateTime = Annotated[
    datetime,
    AfterValidator(validate_timezone_aware),
]
