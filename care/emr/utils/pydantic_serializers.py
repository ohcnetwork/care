from decimal import Decimal
from typing import Annotated

from pydantic.functional_serializers import PlainSerializer

CareDecimal = Annotated[Decimal, PlainSerializer(lambda x: str(x), return_type=str)]
