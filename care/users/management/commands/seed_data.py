from django.core.management import BaseCommand
from care.facility.models.inventory import (
    FacilityInventoryItemTag,
    FacilityInventoryUnit,
    FacilityInventoryItem,
    FacilityInventoryUnitConverter,
)


class Command(BaseCommand):
    """
    Command to add data related to inventory and their conversion rates
    """

    help = "Seed Data for Inventory"

    def handle(self, *args, **options):

        print("Creating Units for Inventory as well as their conversion rates")

        # Inventory Unit

        items, _ = FacilityInventoryUnit.objects.get_or_create(name="Items")
        dozen, _ = FacilityInventoryUnit.objects.get_or_create(name="Dozen")
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

        rice, _ = FacilityInventoryItem.objects.get_or_create(
            name="Rice", default_unit=kg, min_quantity=2
        )
        rice.tags.add(food)
        rice.allowed_units.add(kg, gram)

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

        gaseous_oxygen, _ = FacilityInventoryItem.objects.get_or_create(
            name="Gaseous Oxygen", default_unit=cubic_meter, min_quantity=10
        )
        gaseous_oxygen.tags.add(medical)
        gaseous_oxygen.allowed_units.add(cubic_meter)

        # Conversion Rates

        _, _ = FacilityInventoryUnitConverter.objects.get_or_create(
            from_unit=gram, to_unit=kg, multiplier=0.001
        )

        _, _ = FacilityInventoryUnitConverter.objects.get_or_create(
            from_unit=dozen, to_unit=items, multiplier=12
        )
