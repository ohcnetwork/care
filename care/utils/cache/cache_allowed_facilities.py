from django.core.cache import cache

from care.facility.models.facility import FacilityUser


def get_accessible_facilities(user):
    user_id = str(user.id)
    key = "user_facilities:" + user_id
    hit = cache.get(key)
    if not hit:
        facility_ids = list(
            FacilityUser.objects.filter(user_id=user_id).values_list(
                "facility__id", flat=True
            )
        )
        cache.set(key, facility_ids)
        return facility_ids
    return hit
