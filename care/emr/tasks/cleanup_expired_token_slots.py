from logging import Logger

from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.paginator import Paginator
from django.utils import timezone

from care.emr.models import TokenBooking, TokenSlot

logger: Logger = get_task_logger(__name__)


def convert_token_slot_to_dict(token_slot: TokenSlot):
    return {
        "resource_user_id": token_slot.resource.user_id,
        "resource_facility_id": token_slot.resource.facility_id,
        "availability": {
            "name": token_slot.availability.name,
            "tokens_per_slot": token_slot.availability.tokens_per_slot,
        },
        "start_datetime": token_slot.start_datetime.isoformat(),
        "end_datetime": token_slot.end_datetime.isoformat(),
        "allocated": token_slot.allocated,
    }


def dump_expired_token_slots_to_booking_meta():
    """
    Dumps expired token slots to related booking's meta and unlinks those token booking and token slot objects.
    """
    logger.info("Dumping expired token slots to booking's meta")

    queryset = TokenSlot.objects.filter(
        tokenbooking__isnull=False, end_datetime__lte=timezone.now()
    ).order_by("id")

    paginator = Paginator(queryset, 100)
    for page_number in paginator.page_range:
        bulk_token_booking = []
        for token_slot in paginator.page(page_number).object_list:
            token_slot_meta = convert_token_slot_to_dict(token_slot)
            token_bookings = token_slot.tokenbooking_set.all()
            for token_booking in token_bookings:
                token_booking.meta["token_slot"] = token_slot_meta
                token_booking.token_slot = None
                bulk_token_booking.append(token_booking)
        TokenBooking.objects.bulk_update(bulk_token_booking, ["meta"])


def delete_expired_token_slots():
    """
    Hard-deletes TokenSlot objects that have expired if they have no bookings associated with them.
    """
    logger.info("Cleaning up expired TokenSlot objects")
    queryset = TokenSlot.objects.filter(
        tokenbooking__isnull=True, end_datetime__lte=timezone.now()
    )
    queryset.delete()


@shared_task
def cleanup_expired_token_slots():
    dump_expired_token_slots_to_booking_meta()
    delete_expired_token_slots()
