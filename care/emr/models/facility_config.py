from django.core.cache import cache
from django.db import models

from care.emr.models import EMRBaseModel


class FacilityMonetoryConfig(EMRBaseModel):
    facility = models.OneToOneField(
        "facility.Facility", on_delete=models.CASCADE, unique=True
    )
    discount_codes = models.JSONField(default=list)
    discount_monetary_components = models.JSONField(default=list)
    discount_configuration = models.JSONField(default=dict, null=True, blank=True)
    invoice_number_expression = models.CharField(
        max_length=1000, blank=True, null=True, default=None
    )

    @classmethod
    def get_monetory_config(cls, facility_id):
        obj = cls.objects.filter(facility_id=facility_id).first()
        if not obj:
            obj = cls.objects.create(facility_id=facility_id)
        return obj

    @classmethod
    def get_component_key(cls, component):
        return (
            component.get("code", {}).get("system", "")
            + "/"
            + component.get("code", {}).get("code", "")
        )

    @classmethod
    def get_monetory_component_cache_key(cls, facility_id):
        return f"facility:{facility_id}:monetory_component"

    @classmethod
    def get_discount_configuration_cache_key(cls, facility_id):
        return f"facility:{facility_id}:discount_configuration"

    @classmethod
    def calculate_monetory_components(cls, components):
        component_cache = {}
        for component in components:
            component_cache[cls.get_component_key(component)] = component
        return component_cache

    @classmethod
    def get_monetory_component(cls, facility_id):
        cached_data = cache.get(cls.get_monetory_component_cache_key(facility_id))
        if cached_data:
            return cached_data
        facility = cls.get_monetory_config(facility_id)
        monetory_component = cls.calculate_monetory_components(
            facility.discount_monetary_components
        )
        cache.set(cls.get_monetory_component_cache_key(facility_id), monetory_component)
        return monetory_component

    @classmethod
    def get_discount_configuration(cls, facility_id):
        cached_data = cache.get(cls.get_discount_configuration_cache_key(facility_id))
        if cached_data:
            return cached_data
        facility = cls.get_monetory_config(facility_id)
        discount_configuration = facility.discount_configuration
        if not discount_configuration:
            discount_configuration = {}
        cache.set(
            cls.get_discount_configuration_cache_key(facility_id),
            discount_configuration,
        )
        return discount_configuration

    def save(self, *args, **kwargs):
        cache.delete(self.get_monetory_component_cache_key(self.facility_id))
        cache.delete(self.get_discount_configuration_cache_key(self.facility_id))
        super().save(*args, **kwargs)
