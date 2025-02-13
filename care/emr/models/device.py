from django.contrib.postgres.fields import ArrayField
from django.db import models

from care.emr.models import EMRBaseModel


class Device(EMRBaseModel):
    # Device Data
    identifier = models.CharField(max_length=1024, null=True, blank=True)
    status = models.CharField(max_length=16)
    availability_status = models.CharField(max_length=14)
    manufacturer = models.CharField(max_length=1024)
    manufacture_date = models.DateTimeField(null=True, blank=True)
    expiration_date = models.DateTimeField(null=True, blank=True)
    lot_number = models.CharField(max_length=1024, null=True, blank=True)
    serial_number = models.CharField(max_length=1024, null=True, blank=True)
    registered_name = models.CharField(max_length=1024, null=True, blank=True)
    user_friendly_name = models.CharField(max_length=1024, null=True, blank=True)
    model_number = models.CharField(max_length=1024, null=True, blank=True)
    part_number = models.CharField(max_length=1024, null=True, blank=True)
    contact = models.JSONField(default=dict)
    care_type = models.CharField(max_length=1024, null=True, blank=True, default=None)
    metadata = models.JSONField(default=dict)

    # Relations
    facility = models.ForeignKey("facility.Facility", on_delete=models.CASCADE)
    managing_organization = models.ForeignKey(
        "emr.FacilityOrganization", on_delete=models.SET_NULL, null=True, blank=True
    )
    current_location = models.ForeignKey(
        "emr.FacilityLocation", on_delete=models.SET_NULL, null=True, blank=True
    )
    current_encounter = models.ForeignKey(
        "emr.Encounter", on_delete=models.SET_NULL, null=True, blank=True
    )

    # metadata
    facility_organization_cache = ArrayField(models.IntegerField(), default=list)

    def save(self, *args, **kwargs):
        from care.emr.models.organization import FacilityOrganization

        facility_root_org = FacilityOrganization.objects.filter(
            org_type="root", facility=self.facility
        ).first()
        orgs = set()
        if facility_root_org:
            orgs = orgs.union({facility_root_org.id})
        if self.managing_organization:
            orgs = orgs.union(
                {
                    *self.managing_organization.parent_cache,
                    self.managing_organization.id,
                }
            )
        self.facility_organization_cache = list(orgs)
        return super().save(*args, **kwargs)


class DeviceEncounterHistory(EMRBaseModel):
    device = models.ForeignKey("emr.Device", on_delete=models.CASCADE)
    encounter = models.ForeignKey("emr.Encounter", on_delete=models.CASCADE)
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)


class DeviceLocationHistory(EMRBaseModel):
    device = models.ForeignKey("emr.Device", on_delete=models.CASCADE)
    location = models.ForeignKey("emr.FacilityLocation", on_delete=models.CASCADE)
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)


class DeviceServiceHistory(EMRBaseModel):
    device = models.ForeignKey(
        Device, on_delete=models.PROTECT, null=False, blank=False
    )
    serviced_on = models.DateTimeField(default=None, null=True, blank=False)
    note = models.TextField(default="", null=True, blank=True)
    edit_history = models.JSONField(default=list)
