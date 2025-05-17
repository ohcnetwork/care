from care.emr.models import Observation
from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.sections.base import BaseSection


def _get_observation_value(o: Observation):
    if o.value is None:
        return BaseSection.DEFAULT_EMPTY
    if disp := o.value.get("display"):
        return disp
    if unit := o.value.get("unit", {}).get("display"):
        v = o.value.get("value")
        if isinstance(v, (int, float)) and getattr(v, "is_integer", lambda: False)():
            v = int(v)
        return f"{v} {unit}" if unit else v
    return o.value.get("value", BaseSection.DEFAULT_EMPTY)


class ObservationSection(BaseSection):
    __model__ = Observation

    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)

        self.register_field("observation", lambda o: o.main_code.get("display"))
        self.register_field("value", lambda o: _get_observation_value)
        self.register_field("date", lambda o: o.effective_datetime or o.created_date)
        self.register_field("status", lambda o: o.status)
        self.register_field("category", lambda o: o.category)
        self.register_field("subject_type", lambda o: o.subject_type)
        self.register_field("subject_id", lambda o: o.subject_id)
        self.register_field("logged_by", lambda o: o.data_entered_by.full_name)
        self.register_field("interpretation", lambda o: o.interpretation)

    def fetch_data(self):
        return Observation.objects.filter(encounter=self.context["encounter"])


SectionRegistry.register("observation", ObservationSection)
