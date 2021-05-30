from care.facility.models import facility
from django.core.management import BaseCommand
from care.facility.models.inventory import FacilityInventoryUnit, FacilityInventoryItem


class Command(BaseCommand):
    """
    """

    help = "Seed Data for Inventory"

    def handle(self, *args, **options):

        print("Creating Units for Inventory")

        kilo_litre, _ = FacilityInventoryUnit.objects.get_or_create(name="Kilo Litre")
        cylinders, _ = FacilityInventoryUnit.objects.get_or_create(name="Cylinders")
        cubic_meter, _ = FacilityInventoryUnit.objects.get_or_create(name="Cubic Meter")

        liquid_oxygen, _ = FacilityInventoryItem.objects.get_or_create(
            name="Liquid Oxygen", default_unit=cubic_meter, min_quantity=100
        )
        liquid_oxygen.allowed_units.add(cubic_meter)

        jumbo_d, _ = FacilityInventoryItem.objects.get_or_create(
            name="Jumbo D Type Oxygen Cylinder", default_unit=cylinders, min_quantity=100
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
