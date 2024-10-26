from care.facility.models import Asset, AssetBed, Bed
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities


def get_asset_bed_queryset(user, queryset=None):
    queryset = AssetBed.objects.all() if queryset is None else queryset
    if user.is_superuser:
        pass
    elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
        queryset = queryset.filter(bed__facility__state=user.state)
    elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
        queryset = queryset.filter(bed__facility__district=user.district)
    else:
        allowed_facilities = get_accessible_facilities(user)
        queryset = queryset.filter(bed__facility__id__in=allowed_facilities)
    return queryset


def get_bed_queryset(user, queryset=None):
    queryset = Bed.objects.all() if queryset is None else queryset
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


def get_asset_queryset(user, queryset=None):
    queryset = Asset.objects.all() if queryset is None else queryset
    if user.is_superuser:
        pass
    elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
        queryset = queryset.filter(current_location__facility__state=user.state)
    elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
        queryset = queryset.filter(current_location__facility__district=user.district)
    else:
        allowed_facilities = get_accessible_facilities(user)
        queryset = queryset.filter(
            current_location__facility__id__in=allowed_facilities
        )
    return queryset
