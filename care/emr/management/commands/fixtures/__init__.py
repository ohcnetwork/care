import secrets
import sys
from decimal import Decimal, localcontext

from faker import Faker
from faker.providers.geo import Provider as GeoProvider

# Override the validate_valueset function to skip validation for fixtures
import care.emr.utils.valueset_coding_type  # isort:skip

sys.modules["care.emr.utils.valueset_coding_type"].validate_valueset = (
    lambda _, __, code: code
)


def safe_coordinate(self, center=None, radius=0.001):
    with localcontext() as ctx:
        ctx.prec = 10
        if center is None:
            return Decimal(
                str(self.generator.random.randint(-180000000, 180000000) / 1000000)
            ).quantize(Decimal(".000001"))
        center = float(center)
        radius = float(radius)
        geo = self.generator.random.uniform(center - radius, center + radius)
        return Decimal(str(geo)).quantize(Decimal(".000001"))


# Monkey patching the coordinate method of Faker's GeoProvider as it conflicts with our Decimal precision settings
GeoProvider.coordinate = safe_coordinate


# Roles with their user types
ROLES_OPTIONS = {
    "Volunteer": "volunteer",
    "Doctor": "doctor",
    "Staff": "staff",
    "Nurse": "nurse",
    "Administrator": "administrator",
    "Facility Admin": "administrator",
}


def generate_unique_indian_phone_number():
    return (
        "+91"
        + secrets.choice(["9", "8", "7", "6"])
        + "".join([str(secrets.randbelow(10)) for _ in range(9)])
    )


def get_faker():
    return Faker("en_IN")
