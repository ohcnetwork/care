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
    def __init__(self, config, context, renderer):
        super().__init__(config, context, renderer)
        self.field_extractors.update(
            {
                "observation": lambda o: o.main_code.get("display")
                if o.main_code
                else self.DEFAULT_EMPTY,
                "value": _get_observation_value,
                "date": lambda o: o.effective_datetime
                or o.created_date
                or self.DEFAULT_EMPTY,
            }
        )

    def fetch_data(self):
        return Observation.objects.filter(encounter=self.context["encounter"])


SectionRegistry.register("observation", ObservationSection)
