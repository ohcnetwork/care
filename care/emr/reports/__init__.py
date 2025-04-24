from care.emr.registries.report_section.report_section import SectionRegistry
from care.emr.reports.utils import (
    AllergySection,
    CareTeamSection,
    DiagnosisSection,
    DischargeAdviceSection,
    FileSection,
    MedicationRequestSection,
    ObservationSection,
    PatientInfoSection,
    SymptomSection,
)

SectionRegistry.register("diagnosis", DiagnosisSection)
SectionRegistry.register("symptom", SymptomSection)
SectionRegistry.register("allergy", AllergySection)
SectionRegistry.register("observation", ObservationSection)
SectionRegistry.register("medication_request", MedicationRequestSection)
SectionRegistry.register("patient", PatientInfoSection)
SectionRegistry.register("care_team", CareTeamSection)
SectionRegistry.register("file", FileSection)
SectionRegistry.register("encounter", DischargeAdviceSection)
