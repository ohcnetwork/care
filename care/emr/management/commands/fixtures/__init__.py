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


def create_object(model, facility, user=None, **kwargs):
    """Shared helper to deserialize a Spec, attach facility/user, and save."""
    obj = model.de_serialize()
    obj.facility = facility
    obj.created_by = user or facility.created_by
    obj.updated_by = user or facility.updated_by
    for key, value in kwargs.items():
        setattr(obj, key, value)
    if hasattr(obj, "calculate_slug"):
        obj.slug = obj.calculate_slug()
    obj.save()
    return obj


def create_resource_category(facility, title, resource_type, **kwargs):
    """Create or return an existing ResourceCategory."""
    from care.emr.models.resource_category import ResourceCategory

    resource_category = ResourceCategory.objects.filter(
        facility=facility, title=title, resource_type=resource_type
    ).first()
    if resource_category:
        return resource_category
    _data = {
        "facility": facility,
        "resource_type": resource_type,
        "title": title,
        "slug": f"{title.lower().replace(' ', '-')}-{resource_type}",
        "created_by": facility.created_by,
        "updated_by": facility.created_by,
        "resource_sub_type": "other",
    }
    if kwargs:
        _data.update(kwargs)
    resource_category = ResourceCategory(**_data)
    resource_category.slug = resource_category.calculate_slug()
    resource_category.save()
    return resource_category


def create_charge_item_definition(facility, title, price=None, **kwargs):
    """Create a ChargeItemDefinition for a facility."""
    from care.emr.models import ChargeItemDefinition

    _data = {
        "facility": facility,
        "status": "active",
        "title": title,
        "created_by": facility.created_by,
        "updated_by": facility.created_by,
        "slug": title.lower().replace(" ", "-").replace(".", ""),
        "version": 1,
    }
    if price:
        _data["price_components"] = [
            {"amount": price, "monetary_component_type": "base"}
        ]
    if kwargs:
        _data.update(kwargs)
    charge_item_definition = ChargeItemDefinition(**_data)
    charge_item_definition.slug = charge_item_definition.calculate_slug()
    charge_item_definition.save()
    return charge_item_definition
