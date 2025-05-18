from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.sections.base import BaseSection
from care.users.models import User


class CareTeamSection(BaseSection):
    __model__ = User

    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)
        self.register_field("name", lambda o: o.full_name)
        self.register_field("role", lambda o: self._get_role_for(o))

    @property
    def _role_map(self):
        return {
            m["user_id"]: m["role"]["display"]
            for m in self.context["encounter"].care_team
            if m.get("user_id") and m.get("role")
        }

    def _get_role_for(self, user: User):
        return self._role_map.get(user.id, "Unknown")

    def fetch_data(self):
        ids = [m["user_id"] for m in self.context["encounter"].care_team]
        return User.objects.filter(id__in=ids)


SectionRegistry.register("care_team", CareTeamSection)
