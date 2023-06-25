from django.core.cache import cache

from care.facility.models.patient_investigation import PatientInvestigation


def get_investigation_id(investigation_external_id):
    key = "investigation_external_id:" + investigation_external_id
    hit = cache.get(key)
    if not hit:
        investigation_id = PatientInvestigation.objects.get(
            external_id=investigation_external_id
        ).id
        cache.set(key, investigation_id)
        return investigation_id
    return hit
