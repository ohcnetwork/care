from django.contrib.postgres.fields import ArrayField
from django.db import models

from care.emr.models import EMRBaseModel, FacilityOrganization, TokenBooking


class Encounter(EMRBaseModel):
    status = models.CharField(max_length=100, null=True, blank=True)
    status_history = models.JSONField(default=dict)
    encounter_class = models.CharField(max_length=100, null=True, blank=True)
    encounter_class_history = models.JSONField(default=dict)
    patient = models.ForeignKey("emr.Patient", on_delete=models.CASCADE)
    period = models.JSONField(default=dict)
    facility = models.ForeignKey("facility.Facility", on_delete=models.PROTECT)
    appointment = models.ForeignKey(
        TokenBooking, on_delete=models.SET_NULL, null=True, blank=True
    )
    hospitalization = models.JSONField(default=dict)
    priority = models.CharField(max_length=100, null=True, blank=True)
    external_identifier = models.CharField(max_length=100, null=True, blank=True)
    # Organization fields
    facility_organization_cache = ArrayField(models.IntegerField(), default=list)

    def sync_organization_cache(self):
        orgs = set()
        for encounter_organization in EncounterOrganization.objects.filter(
            encounter=self
        ):
            orgs = orgs.union(
                {
                    *encounter_organization.organization.parent_cache,
                    encounter_organization.organization.id,
                }
            )

        facility_root_org = FacilityOrganization.objects.filter(
            org_type="root", facility=self.facility
        ).first()
        if facility_root_org:
            orgs = orgs.union({facility_root_org.id})

        self.facility_organization_cache = list(orgs)
        super().save(update_fields=["facility_organization_cache"])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.sync_organization_cache()


class EncounterOrganization(EMRBaseModel):
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE)
    organization = models.ForeignKey(
        "emr.FacilityOrganization", on_delete=models.CASCADE
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.encounter.sync_organization_cache()
