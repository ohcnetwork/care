import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models

from care.emr.models import EMRBaseModel
from care.emr.models.organization import FacilityOrganization, Organization


class Questionnaire(EMRBaseModel):
    internal_revision = models.IntegerField(default=1)
    latest_revision = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True
    )
    questions_hash = models.CharField(max_length=255)
    facility = models.ForeignKey(
        "facility.Facility", on_delete=models.CASCADE, null=True, blank=True
    )
    facility_organization = models.ForeignKey(
        "emr.FacilityOrganization", on_delete=models.CASCADE, null=True, blank=True
    )
    version = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, default=uuid.uuid4)
    auth_context = models.CharField(max_length=255, default="instance")
    title = models.CharField(max_length=255)
    description = models.TextField(default="")
    subject_type = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    styling_metadata = models.JSONField(default=dict)
    questions = models.JSONField(default=dict)
    organization_cache = ArrayField(models.IntegerField(), default=list)
    internal_organization_cache = ArrayField(models.IntegerField(), default=list)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["slug"],
                condition=models.Q(
                    deleted=False,
                    auth_context="instance",
                    latest_revision__isnull=True,
                ),
                name="unique_questionnaire_slug_instance",
            ),
            models.UniqueConstraint(
                fields=["slug", "facility", "created_by"],
                condition=models.Q(
                    deleted=False,
                    auth_context="user",
                    latest_revision__isnull=True,
                ),
                name="unique_questionnaire_slug_user",
            ),
            models.UniqueConstraint(
                fields=["slug", "facility"],
                condition=models.Q(
                    deleted=False,
                    auth_context="facility",
                    latest_revision__isnull=True,
                ),
                name="unique_questionnaire_slug_facility",
            ),
            models.UniqueConstraint(
                fields=["slug", "facility_organization"],
                condition=models.Q(
                    deleted=False,
                    auth_context="facility_organization",
                    latest_revision__isnull=True,
                ),
                name="unique_questionnaire_slug_facility_organization",
            ),
        ]

    def get_questions_by_id(self) -> dict:
        cached_result = getattr(self, "_questions_by_id_cache", None)
        if cached_result is not None:
            return cached_result

        questions_dict = {}

        def process_question(question: dict):
            question_id = question.get("id")
            if question_id:
                questions_dict[str(question_id)] = question

            nested_questions = question.get("questions", [])
            if nested_questions:
                for nested_question in nested_questions:
                    process_question(nested_question)

        questions_list = self.questions if isinstance(self.questions, list) else []
        for question in questions_list:
            process_question(question)

        self._questions_by_id_cache = questions_dict
        return questions_dict

    def sync_facility_org_cache(self):
        questionnaire_organization_objects = (
            QuestionnaireFacilityOrganization.objects.filter(questionnaire=self)
        )
        cache = []
        for questionnaire_organization in questionnaire_organization_objects:
            cache.extend(questionnaire_organization.organization.parent_cache)
            cache.append(questionnaire_organization.organization.id)
        cache = list(set(cache))
        self.internal_organization_cache = cache
        self.save(update_fields=["internal_organization_cache"])

    def sync_org_cache(self):
        questionnaire_organization_objects = QuestionnaireOrganization.objects.filter(
            questionnaire=self
        )
        cache = []
        for questionnaire_organization in questionnaire_organization_objects:
            cache.extend(questionnaire_organization.organization.parent_cache)
            cache.append(questionnaire_organization.organization.id)
        cache = list(set(cache))
        self.organization_cache = cache
        self.save(update_fields=["organization_cache"])


class FormSubmission(EMRBaseModel):
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE)
    patient = models.ForeignKey("emr.Patient", on_delete=models.CASCADE)
    encounter = models.ForeignKey(
        "emr.Encounter", on_delete=models.CASCADE, null=True, blank=True
    )
    status = models.CharField(max_length=255)
    response_dump = models.JSONField(default=dict)


class QuestionnaireResponse(EMRBaseModel):
    questionnaire = models.ForeignKey(
        Questionnaire, on_delete=models.CASCADE, null=True, blank=True
    )
    revision = models.IntegerField(default=1)
    subject_id = models.UUIDField()
    responses = models.JSONField(default=list)
    cleaned_response = models.JSONField(default=dict)
    structured_responses = models.JSONField(default=dict)
    structured_response_type = models.CharField(default=None, blank=True, null=True)
    patient = models.ForeignKey("emr.Patient", on_delete=models.CASCADE)
    encounter = models.ForeignKey(
        "emr.Encounter", on_delete=models.CASCADE, null=True, blank=True
    )
    form_submission = models.ForeignKey(
        FormSubmission, on_delete=models.CASCADE, null=True, blank=True
    )
    status = models.CharField(max_length=255, default="completed")
    # TODO : Add index for subject_id and subject_type in descending order

    @property
    def resolved_questionnaire(self):
        if not self.questionnaire:
            return None
        if self.revision == self.questionnaire.internal_revision:
            return self.questionnaire
        return Questionnaire.objects.get(
            latest_revision_id=self.questionnaire_id,
            internal_revision=self.revision,
        )

    def render_responses(self):
        """
        Convert the responses into a human understandable JSON
        with the questionnaire revision used for the response.
        """
        responses = self.responses
        structured_responses = []
        if not responses:
            return structured_responses
        questionnaire = self.resolved_questionnaire
        if not questionnaire:
            return structured_responses
        questions_by_id = questionnaire.get_questions_by_id()
        for response in responses:
            if response["question_id"] not in questions_by_id:
                continue
            structured_responses.append(
                {
                    "answer": response,
                    "question": questions_by_id[response["question_id"]],
                }
            )
        return structured_responses


class QuestionnaireOrganization(EMRBaseModel):
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)


class QuestionnaireFacilityOrganization(EMRBaseModel):
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE)
    organization = models.ForeignKey(FacilityOrganization, on_delete=models.CASCADE)


class QuestionnaireResponseTemplate(EMRBaseModel):
    facility = models.ForeignKey(
        "facility.Facility", on_delete=models.CASCADE, null=True, blank=True
    )
    name = models.CharField(max_length=255)
    description = models.TextField(default="")
    template_data = models.JSONField(default=dict)
    questionnaire = models.ForeignKey(
        Questionnaire, on_delete=models.CASCADE, null=True, blank=True, default=None
    )
    facility_organizations = ArrayField(models.IntegerField(), default=list)
    users = ArrayField(models.IntegerField(), default=list)
    available_keys = ArrayField(models.CharField(max_length=255), default=list)


"""
- Guard questionnaire submit so that other facilities cannot submit their forms
- Ensure Questionnaire valuesets are from the same facility or instance
"""
