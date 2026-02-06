from types import SimpleNamespace

from faker import Faker

from care.emr.models.questionnaire import Questionnaire, QuestionnaireResponse
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)
from care.emr.reports.context_builder.data_points.user import (
    SingleUserRelatedContextBuilder,
)


class QuestionnaireResponsesContextBuilder(QuerysetContextBuilder):
    def get_context(self):
        return self.parent_context.render_responses()

    question = Field(
        display="Question",
        preview_value={
            "code": {
                "code": "8480-6",
                "system": "http://loinc.org",
                "display": "Systolic blood pressure",
            },
            "text": "Systolic Blood Pressure",
            "type": "decimal",
            "unit": {
                "code": "[degF]",
                "system": "http://unitsofmeasure.org",
                "display": "degrees Fahrenheit",
            },
        },
        description="Question of the questionnaire response",
    )
    answer = Field(
        display="Answer",
        preview_value={"values": [{"value": "123"}]},
        description="Value of the response",
    )

    def __iter__(self):
        if self.is_preview:
            return iter(self.__class__(is_preview=True) for c in range(3))
        return iter(
            self.__class__(
                context=SimpleNamespace(answer=c["answer"], question=c["question"])
            )
            for c in self.context
        )


class QuestionnaireContextBuilder(QuerysetContextBuilder):
    title = Field(
        display="Title",
        mapping=lambda obj: obj.questionnaire.title,
        preview_fn=lambda: Faker().catch_phrase(),
        description="Title of the questionnaire",
    )
    description = Field(
        display="Description",
        mapping=lambda obj: obj.questionnaire.description,
        preview_fn=lambda: Faker().catch_phrase(),
        description="Description of the questionnaire",
    )
    responses = Field(
        target_context=QuestionnaireResponsesContextBuilder,
        display="Responses",
        preview_value="",
        description="Responses of the questionnaire",
    )

    updated_by = Field(
        display="Updated By",
        target_context=SingleUserRelatedContextBuilder,
        preview_value="",
        description="User who last updated the questionnaire",
    )

    def get_context(self):
        return QuestionnaireResponse.objects.filter(
            encounter=self.parent_context, questionnaire__isnull=False
        )

    def perform_extra_filters(self, qs, **kwargs):
        if "slug" not in kwargs:
            raise ValueError("slug is required")
        questionnaire = Questionnaire.objects.get(slug=kwargs["slug"])
        return qs.filter(questionnaire=questionnaire).order_by("-created_date")
