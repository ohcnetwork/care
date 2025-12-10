from faker import Faker

from care.emr.reports.context_builder.data_points.base import (
    Field,
    SingleObjectContextBuilder,
)
from care.users.models import User


class SingleUserRelatedContextBuilder(SingleObjectContextBuilder):
    def get_context(self):
        return getattr(self.parent_context, self.parent_attribute)

    full_name = Field(
        display="Full Name",
        mapping="full_name",
        preview_fn=lambda: Faker().name(),
        description="Full name of the user",
    )
    id = Field(
        display="ID",
        mapping="id",
        preview_value="",
        description="ID of the user",
    )


class SingleUserIdContextBuilder(SingleUserRelatedContextBuilder):
    def get_context(self):
        return User.objects.get(id=getattr(self.parent_context, self.parent_attribute))
