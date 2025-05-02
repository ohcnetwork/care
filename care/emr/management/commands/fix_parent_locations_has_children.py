import logging

from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from care.emr.models.location import FacilityLocation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """ """

    help = "Fixes FacilityLocation's has_children being False for parent locations with children"

    def handle(self, *args, **options):
        queryset = FacilityLocation.objects.annotate(
            children_count=Count(
                "facilitylocation", filter=Q(facilitylocation__deleted=False)
            )
        ).filter(children_count__gt=0, has_children=False)
        count = queryset.update(has_children=True)
        logger.info(
            "Fixed %d FacilityLocation objects where has_children was never set to true but actually had children instances",
            count,
        )
