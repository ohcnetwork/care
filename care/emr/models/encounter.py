from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction

from care.emr.models.base import EMRBaseModel
from care.emr.models.scheduling.booking import TokenBooking
from care.emr.resources.patient_identifier.default_expression_evaluator import (
    evaluate_patient_facility_default_values,
)


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

    care_team = models.JSONField(default=dict)
    # Cache users to avoid Json Queries
    care_team_users = ArrayField(models.IntegerField(), default=list)

    # Organization fields
    facility_organization_cache = ArrayField(models.IntegerField(), default=list)

    current_location = models.ForeignKey(
        "emr.FacilityLocation", on_delete=models.SET_NULL, null=True, blank=True
    )  # Cached field, used for easier querying

    discharge_summary_advice = models.TextField(null=True, blank=True)

    tags = ArrayField(models.IntegerField(), default=list)

    extensions = models.JSONField(default=dict)

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

        orgs = orgs.union({self.facility.default_internal_organization_id})

        self.facility_organization_cache = list(orgs)
        super().save(update_fields=["facility_organization_cache"])

    def sync_care_team_users_cache(self):
        if isinstance(self.care_team, list):
            self.care_team_users = [int(x.get("user_id", -1)) for x in self.care_team]

    def save(self, *args, **kwargs):
        created = False
        self.sync_care_team_users_cache()
        if not self.pk:
            # Generate Facility identifiers for this encounter
            created = True
        with transaction.atomic():
            super().save(*args, **kwargs)
            if created:
                evaluate_patient_facility_default_values(self.patient, self.facility)
        self.sync_organization_cache()


class EncounterOrganization(EMRBaseModel):
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE)
    organization = models.ForeignKey(
        "emr.FacilityOrganization", on_delete=models.CASCADE
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.encounter.sync_organization_cache()
