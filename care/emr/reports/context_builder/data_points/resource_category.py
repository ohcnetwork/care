from care.emr.models.resource_category import ResourceCategory
from care.emr.reports.context_builder.data_points.base import (
    Field,
    SingleObjectContextBuilder,
)


class ResourceCategoryContextBuilder(SingleObjectContextBuilder):
    def get_context(self):
        return ResourceCategory.objects.get(
            id=getattr(self.parent_context, self.parent_attribute)
        )

    title = Field(
        display="Resource Category Title",
        preview_value="General Supplies",
        mapping=lambda rc: rc.title,
        description="Title of the resource category",
    )
    description = Field(
        display="Resource Category Description",
        preview_value="Category for general medical supplies",
        mapping=lambda rc: rc.description,
        description="Description of the resource category",
    )


class ResourceCategoryObjectContextBuilder(ResourceCategoryContextBuilder):
    def get_context(self):
        return self.parent_context.get("category")
