from care.facility.models.facility import Facility
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities


def get_facility_queryset(user):
    queryset = Facility.objects.all()
    if user.is_superuser:
        pass
    elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
        queryset = queryset.filter(state=user.state)
    elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
        queryset = queryset.filter(district=user.district)
    else:
        allowed_facilities = get_accessible_facilities(user)
        queryset = queryset.filter(id__in=allowed_facilities)
    return queryset
