from django.core.management import BaseCommand

from care.facility.models.inventory import (
    FacilityInventoryItem,
    FacilityInventoryItemTag,
    FacilityInventoryUnit,
    FacilityInventoryUnitConverter,
)


class Command(BaseCommand):
    """
    Command to add data related to inventory and their conversion rates
    """

    help = "Seed Data for Inventory"

    def handle(self, *args, **kwargs):
        # Inventory Unit

        items, _ = FacilityInventoryUnit.objects.get_or_create(name="Items")
        dozen, _ = FacilityInventoryUnit.objects.get_or_create(name="Dozen")
        kilo_litre, _ = FacilityInventoryUnit.objects.get_or_create(name="Kilo Litre")
        cylinders, _ = FacilityInventoryUnit.objects.get_or_create(name="Cylinders")
        kg, _ = FacilityInventoryUnit.objects.get_or_create(name="kg")
        gram, _ = FacilityInventoryUnit.objects.get_or_create(name="gram")
        cubic_meter, _ = FacilityInventoryUnit.objects.get_or_create(name="Cubic Meter")

        # Inventory Tags

        safety, _ = FacilityInventoryItemTag.objects.get_or_create(name="Safety")
        medical, _ = FacilityInventoryItemTag.objects.get_or_create(name="Medical")
        food, _ = FacilityInventoryItemTag.objects.get_or_create(name="Food")

        # Inventory Item

        ppe, _ = FacilityInventoryItem.objects.get_or_create(
            name="PPE", default_unit=items, min_quantity=150
        )
        ppe.tags.add(safety, medical)
        ppe.allowed_units.add(items, dozen)

        fluid, _ = FacilityInventoryItem.objects.get_or_create(
            name="IV Fluid 500 ml", default_unit=items, min_quantity=2
        )
        fluid.tags.add(medical)
        fluid.allowed_units.add(items, dozen)

        liquid_oxygen, _ = FacilityInventoryItem.objects.get_or_create(
            name="Liquid Oxygen", default_unit=cubic_meter, min_quantity=10
        )
        liquid_oxygen.tags.add(medical)
        liquid_oxygen.allowed_units.add(cubic_meter)

        jumbo_d, _ = FacilityInventoryItem.objects.get_or_create(
            name="Jumbo D Type Oxygen Cylinder",
            default_unit=cylinders,
            min_quantity=100,
        )
        jumbo_d.allowed_units.add(cylinders)

        type_b, _ = FacilityInventoryItem.objects.get_or_create(
            name="B Type Oxygen Cylinder", default_unit=cylinders, min_quantity=100
        )
        type_b.allowed_units.add(cylinders)

        type_c, _ = FacilityInventoryItem.objects.get_or_create(
            name="C Type Oxygen Cylinder", default_unit=cylinders, min_quantity=100
        )
        type_c.allowed_units.add(cylinders)

        gaseous_oxygen, _ = FacilityInventoryItem.objects.get_or_create(
            name="Gaseous Oxygen", default_unit=cubic_meter, min_quantity=10
        )
        gaseous_oxygen.tags.add(medical)
        gaseous_oxygen.allowed_units.add(cubic_meter)

        # Conversion Rates

        _, _ = FacilityInventoryUnitConverter.objects.get_or_create(
            from_unit=kg, to_unit=gram, multiplier=1000
        )

        _, _ = FacilityInventoryUnitConverter.objects.get_or_create(
            from_unit=dozen, to_unit=items, multiplier=12
        )
