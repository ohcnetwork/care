from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models

from care.emr.models.base import EMRBaseModel


class ReferralAvailability(EMRBaseModel):
    entity_type = models.CharField(max_length=100)
    external_organization = models.ForeignKey(
        "emr.Organization", on_delete=models.PROTECT, null=True, blank=True
    )
    internal_organization = models.ForeignKey(
        "emr.FacilityOrganization", on_delete=models.PROTECT, null=True, blank=True
    )
    facility = models.ForeignKey(
        "facility.Facility", on_delete=models.PROTECT, null=True, blank=True
    )
    external_entity = models.JSONField(default=dict)
    status = models.CharField(max_length=100, default="draft", db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(default="")
    is_public = models.BooleanField(default=False)
    care_team = models.JSONField(default=list)
    referral_type = models.CharField(max_length=100)
    questionnaires = models.ManyToManyField(
        "emr.Questionnaire", through="ReferralAvailabilityQuestionnaire", blank=True
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        entity_type="external_organization",
                        external_organization__isnull=False,
                        internal_organization__isnull=True,
                        facility__isnull=True,
                    )
                    | models.Q(
                        entity_type="internal_organization",
                        external_organization__isnull=True,
                        internal_organization__isnull=False,
                    )
                    | models.Q(
                        entity_type="facility",
                        external_organization__isnull=True,
                        internal_organization__isnull=True,
                        facility__isnull=False,
                    )
                    | models.Q(
                        entity_type="external",
                        external_organization__isnull=True,
                        internal_organization__isnull=True,
                        facility__isnull=True,
                    )
                ),
                name="referral_availability_target",
            )
        ]


class ReferralAvailabilityQuestionnaire(models.Model):
    availability = models.ForeignKey(
        ReferralAvailability,
        on_delete=models.CASCADE,
        related_name="questionnaire_mappings",
        db_column="referralavailability_id",
    )
    questionnaire = models.ForeignKey(
        "emr.Questionnaire",
        on_delete=models.CASCADE,
        related_name="referral_availability_mappings",
    )
    questionnaire_type = models.CharField(max_length=100, default="request")

    class Meta:
        db_table = "emr_referralavailability_questionnaires"
        unique_together = [("availability", "questionnaire")]

    def __str__(self):
        return f"{self.availability_id}: {self.questionnaire_id} ({self.questionnaire_type})"


class Referral(EMRBaseModel):
    availability = models.ForeignKey(
        ReferralAvailability, on_delete=models.PROTECT, related_name="referrals"
    )
    patient = models.ForeignKey("emr.Patient", on_delete=models.PROTECT)
    encounter = models.ForeignKey(
        "emr.Encounter", on_delete=models.PROTECT, null=True, blank=True
    )
    title = models.CharField(max_length=255)
    note = models.TextField(default="")
    status = models.CharField(max_length=100, default="pending", db_index=True)
    assignees = models.JSONField(default=list)
    # Cache the care-team users for the pending referral inbox.
    assignee_users = ArrayField(models.IntegerField(), default=list)
    thread = models.OneToOneField(
        "emr.NoteThread",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="referral",
    )

    class Meta:
        indexes = [GinIndex(fields=["assignee_users"], name="referral_assignees_gin")]

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if update_fields is None or "assignees" in update_fields:
            self.assignee_users = list(
                dict.fromkeys(member["user_id"] for member in self.assignees)
            )
            if update_fields is not None:
                kwargs["update_fields"] = {*update_fields, "assignee_users"}
        super().save(*args, **kwargs)


class ReferralQuestionnaireResponse(EMRBaseModel):
    referral = models.ForeignKey(
        Referral, on_delete=models.CASCADE, related_name="questionnaire_responses"
    )
    questionnaire = models.ForeignKey("emr.Questionnaire", on_delete=models.PROTECT)
    questionnaire_response = models.JSONField(default=dict)
    questionnaire_revision = models.PositiveIntegerField(default=1)
    questionnaire_snapshot = models.JSONField(default=dict)
    status = models.CharField(max_length=100, default="completed")
    questionnaire_type = models.CharField(max_length=100, default="request")


class ReferralResource(EMRBaseModel):
    referral = models.ForeignKey(
        Referral, on_delete=models.CASCADE, related_name="resources"
    )
    resource_type = models.CharField(max_length=100)
    resource_id = models.UUIDField()
    attachment_type = models.CharField(max_length=100, default="source")
    metadata = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(
                fields=["resource_type", "resource_id"],
                condition=models.Q(deleted=False),
                name="referral_resource_reverse_idx",
            )
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["referral", "resource_type", "resource_id"],
                condition=models.Q(deleted=False),
                name="unique_referral_resource",
            )
        ]
