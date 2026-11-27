from django.db import models

from care.emr.models.base import EMRBaseModel


class FacilityResourceQuestionnaireResponse(EMRBaseModel):
    facility = models.ForeignKey("facility.Facility", on_delete=models.CASCADE)
    questionnaire = models.ForeignKey("emr.Questionnaire", on_delete=models.CASCADE)
    revision = models.IntegerField(default=1)
    subject_type = models.CharField(max_length=255)
    subject_id = models.UUIDField()
    responses = models.JSONField(default=list)
    cleaned_response = models.JSONField(default=dict)
    structured_responses = models.JSONField(default=dict)
    structured_response_type = models.CharField(default=None, blank=True, null=True)
    status = models.CharField(max_length=255, default="completed")

    @property
    def resolved_questionnaire(self):
        if self.revision == self.questionnaire.internal_revision:
            return self.questionnaire
        return self.questionnaire.__class__.objects.get(
            latest_revision_id=self.questionnaire_id,
            internal_revision=self.revision,
        )

    def render_responses(self):
        responses = []
        questions_by_id = self.resolved_questionnaire.get_questions_by_id()
        for response in self.responses:
            if response["question_id"] not in questions_by_id:
                continue
            responses.append(
                {
                    "answer": response,
                    "question": questions_by_id[response["question_id"]],
                }
            )
        return responses


class FacilityResourceObservation(EMRBaseModel):
    facility = models.ForeignKey("facility.Facility", on_delete=models.CASCADE)
    status = models.CharField(max_length=255)
    is_group = models.BooleanField(default=False)
    category = models.JSONField(default=dict)
    main_code = models.JSONField(default=dict)
    alternate_coding = models.JSONField(default=list)
    subject_type = models.CharField(max_length=255)
    subject_id = models.UUIDField()
    effective_datetime = models.DateTimeField(null=True, blank=True, default=None)
    data_entered_by = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="resource_observations_entered",
        null=True,
        blank=True,
        default=None,
    )
    performer = models.JSONField(default=dict)
    value_type = models.CharField(max_length=255)
    value = models.JSONField()
    note = models.TextField()
    method = models.JSONField(default=dict)
    reference_range = models.JSONField(default=list)
    interpretation = models.JSONField(default=dict)
    parent = models.UUIDField(null=True)
    questionnaire_response = models.ForeignKey(
        "emr.FacilityResourceQuestionnaireResponse", on_delete=models.CASCADE, null=True
    )
    component = models.JSONField(default=list)
    observation_definition = models.ForeignKey(
        "emr.ObservationDefinition",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
    )
