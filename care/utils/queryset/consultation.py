from django.db.models.query_utils import Q

from care.facility.models.patient_consultation import PatientConsultation
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities


def get_consultation_queryset(user):
    queryset = PatientConsultation.objects.all()
    if user.is_superuser:
        pass
    elif hasattr(user, "asset") and user.asset is not None:
        queryset = queryset.filter(facility=user.asset.current_location.facility_id)
    elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
        q_filters = Q(facility__state=user.state)
        q_filters |= Q(patient__facility__state=user.state)
        queryset = queryset.filter(q_filters)
    elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
        q_filters = Q(facility__district=user.district)
        q_filters |= Q(patient__facility__district=user.district)
        queryset = queryset.filter(q_filters)
    else:
        allowed_facilities = get_accessible_facilities(user)
        q_filters = Q(facility__id__in=allowed_facilities)
        q_filters |= Q(patient__facility__id__in=allowed_facilities)
        q_filters |= Q(assigned_to=user)
        q_filters |= Q(patient__assigned_to=user)
        queryset = queryset.filter(q_filters)
    return queryset
