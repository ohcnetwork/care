import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models

from care.emr.models import EMRBaseModel
from care.emr.models.organization import FacilityOrganization, Organization

TAG_CACHE = {}  # TODO change to Redis with LRU Cache in process
MAX_QUESTIONNAIRE_TAGS_COUNT = 1000


class QuestionnaireTag(EMRBaseModel):
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, default=uuid.uuid4, unique=True)

    @classmethod
    def serialize_model(cls, obj):
        return {
            "id": obj.external_id,
            "name": obj.name,
            "slug": obj.slug,
        }

    @classmethod
    def get_tag(cls, tag_id):
        if tag_id in TAG_CACHE:
            return TAG_CACHE[tag_id]
        try:
            tag = cls.objects.get(id=tag_id)
            TAG_CACHE[tag_id] = cls.serialize_model(tag)
            return TAG_CACHE[tag_id]
        except Exception:  # noqa S110
            pass
        return {}

    def save(self, *args, **kwargs):
        if self.__class__.objects.all().count() > MAX_QUESTIONNAIRE_TAGS_COUNT:
            err = f"An instance can have only upto {MAX_QUESTIONNAIRE_TAGS_COUNT} tags"
            raise ValueError(err)
        super().save(*args, **kwargs)
        TAG_CACHE[self.id] = self.serialize_model(self)


class Questionnaire(EMRBaseModel):
    version = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, default=uuid.uuid4, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(default="")
    subject_type = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    styling_metadata = models.JSONField(default=dict)
    questions = models.JSONField(default=dict)
    organization_cache = ArrayField(models.IntegerField(), default=list)
    internal_organization_cache = ArrayField(models.IntegerField(), default=list)
    tags = ArrayField(models.IntegerField(), default=list)

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
    subject_id = models.UUIDField()
    responses = models.JSONField(default=list)
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

    def render_responses(self):
        """
        Convert the responses into a human understandable JSON
        with current questionnaire data
        """
        responses = self.responses
        structured_responses = []
        if not responses:
            return structured_responses
        if not self.questionnaire:
            return structured_responses
        questions_by_id = self.questionnaire.get_questions_by_id()
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
    # TODO Add instance level roles, ie roles would be added here

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.sync_questionnaire_cache()

    def sync_questionnaire_cache(self):
        questionnaire_organization_objects = QuestionnaireOrganization.objects.filter(
            questionnaire=self.questionnaire
        )
        cache = []
        for questionnaire_organization in questionnaire_organization_objects:
            cache.extend(questionnaire_organization.organization.parent_cache)
            cache.append(questionnaire_organization.organization.id)
        cache = list(set(cache))
        self.questionnaire.organization_cache = cache
        self.questionnaire.save(update_fields=["organization_cache"])


class QuestionnaireFacilityOrganization(EMRBaseModel):
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE)
    organization = models.ForeignKey(FacilityOrganization, on_delete=models.CASCADE)
    # TODO Add instance level roles, ie roles would be added here

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.sync_questionnaire_cache()

    def sync_questionnaire_cache(self):
        questionnaire_organization_objects = (
            QuestionnaireFacilityOrganization.objects.filter(
                questionnaire=self.questionnaire
            )
        )
        cache = []
        for questionnaire_organization in questionnaire_organization_objects:
            cache.extend(questionnaire_organization.organization.parent_cache)
            cache.append(questionnaire_organization.organization.id)
        cache = list(set(cache))
        self.questionnaire.internal_organization_cache = cache
        self.questionnaire.save(update_fields=["internal_organization_cache"])


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
