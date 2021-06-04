from care.facility.models.facility import Facility
from care.users.models import User


def get_facility_queryset(user):
    queryset = Facility.objects.all()
    if user.is_superuser:
        pass
    elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
        queryset = queryset.filter(state=user.state)
    elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
        queryset = queryset.filter(district=user.district)
    else:
        queryset = queryset.filter(users__id__exact=user.id)
    return queryset
