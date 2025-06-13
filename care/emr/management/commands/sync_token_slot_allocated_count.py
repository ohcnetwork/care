from django.core.management.base import BaseCommand
from django.db.models import Count, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce

from care.emr.models import TokenBooking, TokenSlot
from care.emr.resources.scheduling.slot.spec import CANCELLED_STATUS_CHOICES


class Command(BaseCommand):
    help = "Sync TokenSlot object's allocated count"

    def handle(self, *args, **options):
        allocated_bookings_subquery = (
            TokenBooking.objects.filter(
                token_slot=OuterRef("pk"),
            )
            .exclude(status__in=CANCELLED_STATUS_CHOICES)
            .values("token_slot")
            .annotate(count=Count("id"))
            .values("count")
        )

        TokenSlot.objects.update(
            allocated=Coalesce(
                Subquery(allocated_bookings_subquery),
                Value(0),
            )
        )
