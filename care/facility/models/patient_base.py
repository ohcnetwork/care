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
ADMIT_CHOICES = [
    (None, "Not admitted"),
    (1, "Isolation Room"),
    (2, "ICU"),
    (3, "ICU with Ventilator"),
    (20, "Home Isolation"),
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
}
DISEASE_CHOICES = [(v, k) for k, v in DISEASE_CHOICES_MAP.items()]

CATEGORY_CHOICES = [
    ("ASYM", "ASYMPTOMATIC"),
    ("Mild", "Category-A"),
    ("Moderate", "Category-B"),
    ("Severe", "Category-C"),
    (None, "UNCLASSIFIED"),
]


class DiseaseStatusEnum(enum.IntEnum):
    SUSPECTED = 1
    POSITIVE = 2
    NEGATIVE = 3
    RECOVERY = 4
    RECOVERED = 5
    EXPIRED = 6


DISEASE_STATUS_CHOICES = [(e.value, e.name) for e in DiseaseStatusEnum]
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
SuggestionChoices = SimpleNamespace(HI="HI", A="A", R="R", OP="OP")

REVERSE_BLOOD_GROUP_CHOICES = reverse_choices(BLOOD_GROUP_CHOICES)
REVERSE_DISEASE_STATUS_CHOICES = reverse_choices(DISEASE_STATUS_CHOICES)
