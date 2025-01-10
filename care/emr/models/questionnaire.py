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
        return {"name": obj.name, "slug": obj.slug}

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

    # TODO : Add index for subject_id and subject_type in descending order


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
