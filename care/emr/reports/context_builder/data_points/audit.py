from care.emr.reports.context_builder.data_points.base import Field
from care.emr.reports.context_builder.data_points.user import (
    SingleUserRelatedContextBuilder,
)


class AuditContextMixin:
    """Audit fields for contexts backed by a model inheriting EMRBaseModel."""

    created_by = Field(
        display="Created By",
        target_context=SingleUserRelatedContextBuilder,
        preview_value="",
        description="User who created the record",
    )
    updated_by = Field(
        display="Updated By",
        target_context=SingleUserRelatedContextBuilder,
        preview_value="",
        description="User who last updated the record",
    )
    created_date = Field(
        display="Created Date",
        preview_value="2026-01-12T10:01:45.088000Z",
        description="Date when the record was created",
    )
    modified_date = Field(
        display="Modified Date",
        preview_value="2026-01-12T10:01:45.088000Z",
        description="Date when the record was last modified",
    )
