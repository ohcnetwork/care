from care.emr.models.condition import Condition
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)
from care.emr.reports.context_builder.data_points.user import (
    SingleUserRelatedContextBuilder,
)


class SymptomsContextBuilder(QuerysetContextBuilder):
    clinical_status = Field(
        key="clinical_status",
        display="Clinical Status",
        preview_value="Active",
        description="Clinical status of the condition",
    )
    verification_status = Field(
        key="verification_status",
        display="Verification Status",
        preview_value="Confirmed",
        description="Verification status of the condition",
    )
    created_by = Field(
        key="created_by",
        display="Created By",
        target_context=SingleUserRelatedContextBuilder,
        preview_value="",
        description="User who created the condition",
    )
    updated_by = Field(
        key="updated_by",
        display="Updated By",
        target_context=SingleUserRelatedContextBuilder,
        preview_value="",
        description="User who updated the condition",
    )

    def get_context(self) -> dict:
        return Condition.objects.filter(encounter=self.parent_context)

    def _filter(self, **kwargs):
        qs = self.context
        if "verification_status" in kwargs:
            qs = qs.filter(verification_status=kwargs["verification_status"])
        if "clinical_status" in kwargs:
            qs = qs.filter(clinical_status=kwargs["clinical_status"])
        return self.get_iterable(qs)
