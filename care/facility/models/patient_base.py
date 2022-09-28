import enum
from types import SimpleNamespace


def reverse_choices(choices):
    output = {}
    for choice in choices:
        output[choice[0]] = choice[1]
    return output


CURRENT_HEALTH_CHOICES = [
    (0, "NO DATA"),
    (1, "REQUIRES VENTILATOR"),
    (2, "WORSE"),
    (3, "STATUS QUO"),
    (4, "BETTER"),
]

SYMPTOM_CHOICES = [
    (1, "ASYMPTOMATIC"),
    (2, "FEVER"),
    (3, "SORE THROAT"),
    (4, "COUGH"),
    (5, "BREATHLESSNESS"),
    (6, "MYALGIA"),
    (7, "ABDOMINAL DISCOMFORT"),
    (8, "VOMITING/DIARRHOEA"),
    (9, "OTHERS"),
    (10, "SARI"),
    (11, "SPUTUM"),
    (12, "NAUSEA"),
    (13, "CHEST PAIN"),
    (14, "HEMOPTYSIS"),
    (15, "NASAL DISCHARGE"),
    (16, "BODY ACHE"),
]

DISEASE_CHOICES_MAP = {
    "NO": 1,
    "Diabetes": 2,
    "Heart Disease": 3,
    "HyperTension": 4,
    "Kidney Diseases": 5,
    "Lung Diseases/Asthma": 6,
    "Cancer": 7,
    "OTHER": 8,
}
DISEASE_CHOICES = [(v, k) for k, v in DISEASE_CHOICES_MAP.items()]

COVID_CATEGORY_CHOICES = [
    ("ASYM", "ASYMPTOMATIC"),
    ("Mild", "Category-A"),
    ("Moderate", "Category-B"),
    ("Severe", "Category-C"),
    (None, "UNCLASSIFIED"),
]  # Deprecated

CATEGORY_CHOICES = [
    ("Comfort", "Comfort Care"),
    ("Stable", "Stable"),
    ("Moderate", "Slightly Abnormal"),
    ("Critical", "Critical"),
]

DISCHARGE_REASON_CHOICES = [
    ("REC", "Recovered"),
    ("REF", "Referred"),
    ("EXP", "Expired"),
    ("LAMA", "LAMA"),
]


class DiseaseStatusEnum(enum.IntEnum):
    SUSPECTED = 1
    POSITIVE = 2
    NEGATIVE = 3
    RECOVERY = 4
    RECOVERED = 5
    EXPIRED = 6


DISEASE_STATUS_CHOICES = [(e.value, e.name) for e in DiseaseStatusEnum]
DISEASE_STATUS_DICT = {}
for i in DISEASE_STATUS_CHOICES:
    DISEASE_STATUS_DICT[i[1]] = i[0]

BLOOD_GROUP_CHOICES = [
    ("A+", "A+"),
    ("A-", "A-"),
    ("B+", "B+"),
    ("B-", "B-"),
    ("AB+", "AB+"),
    ("AB-", "AB-"),
    ("O+", "O+"),
    ("O-", "O-"),
    ("UNK", "UNKNOWN"),
]
SuggestionChoices = SimpleNamespace(HI="HI", A="A", R="R", OP="OP", DC="DC")


class BedType(enum.Enum):
    ISOLATION = 1
    ICU = 2
    ICU_WITH_NON_INVASIVE_VENTILATOR = 3
    ICU_WITH_OXYGEN_SUPPORT = 4
    ICU_WITH_INVASIVE_VENTILATOR = 5
    BED_WITH_OXYGEN_SUPPORT = 6
    REGULAR = 7


BedTypeChoices = [(e.value, e.name) for e in BedType]

REVERSE_BLOOD_GROUP_CHOICES = reverse_choices(BLOOD_GROUP_CHOICES)
REVERSE_DISEASE_STATUS_CHOICES = reverse_choices(DISEASE_STATUS_CHOICES)
REVERSE_COVID_CATEGORY_CHOICES = reverse_choices(COVID_CATEGORY_CHOICES)  # Deprecated
REVERSE_CATEGORY_CHOICES = reverse_choices(CATEGORY_CHOICES)
# REVERSE_ADMIT_CHOICES = reverse_choices(ADMIT_CHOICES)
REVERSE_BED_TYPE_CHOICES = reverse_choices(BedTypeChoices)
