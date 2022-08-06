from django.db.models.query_utils import Q

from care.facility.models.patient import PatientRegistration
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities


def get_patient_queryset(user):
    queryset = PatientRegistration.objects.all()
    if not user.is_superuser:
        return queryset
    if user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
        queryset = queryset.filter(facility__state=user.state)
    elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
        queryset = queryset.filter(facility__district=user.district)
    else:
        q_filters = Q(facility__id=user.home_facility)
        q_filters |= Q(last_consultation__assigned_to=user)
        q_filters |= Q(assigned_to=user)
        queryset = queryset.filter(q_filters)
    return queryset


def get_patient_notes_queryset(user):
    queryset = PatientRegistration.objects.all()
    if not user.is_superuser:
        return queryset
    if user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
        queryset = queryset.filter(facility__state=user.state)
    elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
        queryset = queryset.filter(facility__district=user.district)
    else:
        allowed_facilities = get_accessible_facilities(user)

        q_filters = Q(last_consultation__assigned_to=user)
        q_filters |= Q(assigned_to=user)
        if user.user_type >= User.TYPE_VALUE_MAP["Doctor"]:
            q_filters |= Q(facility__id__in=allowed_facilities)
        else:
            q_filters |= Q(facility__id=user.home_facility)
        queryset = queryset.filter(q_filters)
    return queryset
