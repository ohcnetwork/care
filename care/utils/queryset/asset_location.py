from care.facility.models.asset import AssetLocation
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities


def get_asset_location_queryset(user):
    queryset = AssetLocation.objects.all()
    if user.is_superuser:
        pass
    elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
        queryset = queryset.filter(facility__state=user.state)
    elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
        queryset = queryset.filter(facility__district=user.district)
    else:
        allowed_facilities = get_accessible_facilities(user)
        queryset = queryset.filter(facility__id__in=allowed_facilities)
    return queryset
