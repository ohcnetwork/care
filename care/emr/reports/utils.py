import logging

from care.emr.models import (
    AllergyIntolerance,
    Condition,
    FileUpload,
    Observation,
)
from care.emr.models.medication_request import MedicationRequest
from care.emr.reports.base import BaseSection
from care.emr.resources.condition.spec import CategoryChoices
from care.facility.models import User

logger = logging.getLogger(__name__)


class SymptomSection(BaseSection):
    def __init__(self, config, context):
        super().__init__(config, context)
        self.field_extractors.update(
            {
                "symptom": lambda o: o.code.get("display")
                if o.code
                else self.DEFAULT_EMPTY,
                "onset": lambda o: o.onset.get("onset_datetime")
                if o.onset
                else self.DEFAULT_EMPTY,
            }
        )

    def fetch_data(self):
        return Condition.objects.filter(
            encounter=self.context["encounter"],
            category=CategoryChoices.problem_list_item,
        )


class DiagnosisSection(BaseSection):
    def __init__(self, config, context):
        super().__init__(config, context)
        self.field_extractors.update(
            {
                "diagnosis": lambda o: o.code.get("display")
                if o.code
                else self.DEFAULT_EMPTY,
                "onset": lambda o: o.onset.get("onset_datetime")
                if o.onset
                else self.DEFAULT_EMPTY,
            }
        )

    def fetch_data(self):
        return Condition.objects.filter(
            encounter=self.context["encounter"],
            category=CategoryChoices.encounter_diagnosis,
        )


class AllergySection(BaseSection):
    def __init__(self, config, context):
        super().__init__(config, context)
        self.field_extractors.update(
            {
                "allergen": lambda o: o.code.get("display")
                if o.code
                else self.DEFAULT_EMPTY,
                "onset": lambda o: o.onset.get("onset_datetime")
                if o.onset
                else self.DEFAULT_EMPTY,
            }
        )

    def fetch_data(self):
        return AllergyIntolerance.objects.filter(encounter=self.context["encounter"])


def _get_observation_value(o: Observation):
    if disp := o.value.get("display"):
        return disp
    if unit := o.value.get("unit", {}).get("display"):
        v = o.value.get("value")
        if isinstance(v, (int, float)) and getattr(v, "is_integer", lambda: False)():
            v = int(v)
        return f"{v} {unit}" if unit else v
    return o.value.get("value", BaseSection.DEFAULT_EMPTY)


class ObservationSection(BaseSection):
    def __init__(self, config, context):
        super().__init__(config, context)
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


def _med_dosage(o: MedicationRequest):
    try:
        return o.dosage_instruction[0]["text"] or BaseSection.DEFAULT_EMPTY
    except Exception:
        return BaseSection.DEFAULT_EMPTY


class MedicationRequestSection(BaseSection):
    def __init__(self, config, context):
        super().__init__(config, context)
        self.field_extractors.update(
            {
                "medication": lambda m: m.medication.get("display", self.DEFAULT_EMPTY),
                "value": _med_dosage,
                "date": lambda m: m.authored_on or m.created_date or self.DEFAULT_EMPTY,
            }
        )

    def fetch_data(self):
        return MedicationRequest.objects.filter(encounter=self.context["encounter"])


class PatientInfoSection(BaseSection):
    def fetch_data(self):
        return [self.context["encounter"].patient]


class CareTeamSection(BaseSection):
    def __init__(self, config, context):
        super().__init__(config, context)
        self.field_extractors.update(
            {
                "name": lambda u: u.full_name,
                "role": self._get_role_for,
            }
        )

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


class FileSection(BaseSection):
    def fetch_data(self):
        return FileUpload.objects.filter(
            associating_id=self.context["encounter"].external_id,
            upload_completed=True,
            is_archived=False,
        )


class DischargeAdviceSection(BaseSection):
    def fetch_data(self):
        return [self.context["encounter"].discharge_summary_advice or ""]
