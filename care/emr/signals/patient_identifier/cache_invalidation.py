from django.core.cache import cache
from django.db.models.signals import post_save

from care.emr.models.patient import PatientIdentifierConfig
from care.emr.resources.base import model_cache_key, model_string
from care.facility.models import Facility


def invalidate_facility_cache_on_identifier_change(sender, instance, **kwargs):
    facility_model_string = model_string(Facility)

    if instance.facility_id:
        cache.delete_pattern(
            model_cache_key(facility_model_string, pk=instance.facility.external_id)
        )
    else:
        cache.delete_pattern(model_cache_key(facility_model_string))


post_save.connect(
    invalidate_facility_cache_on_identifier_change,
    sender=PatientIdentifierConfig,
    dispatch_uid="invalidate_facility_cache_on_identifier_config_save",
)
