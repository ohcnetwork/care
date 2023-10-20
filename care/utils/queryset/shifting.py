from django.db.models.query_utils import Q

from care.facility.models.shifting import ShiftingRequest
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities


def get_shifting_queryset(user):
    queryset = ShiftingRequest.objects.all()
    if user.is_superuser:
        pass
    elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
        q_objects = Q(origin_facility__state=user.state)
        q_objects |= Q(shifting_approving_facility__state=user.state)
        q_objects |= Q(assigned_facility__state=user.state)
        queryset = queryset.filter(q_objects)
    elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
        q_objects = Q(origin_facility__district=user.district)
        q_objects |= Q(shifting_approving_facility__district=user.district)
        q_objects |= Q(assigned_facility__district=user.district)
        queryset = queryset.filter(q_objects)
    else:
        facility_ids = get_accessible_facilities(user)
        q_objects = Q(origin_facility__id__in=facility_ids)
        q_objects |= Q(shifting_approving_facility__id__in=facility_ids)
        q_objects |= Q(assigned_facility__id__in=facility_ids, status__gte=20)
        q_objects |= Q(patient__facility__id__in=facility_ids)
        queryset = queryset.filter(q_objects)
    return queryset
