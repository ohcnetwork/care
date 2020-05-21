from types import SimpleNamespace
from collections import namedtuple
# CURRENT_HEALTH_CHOICES = [
#     (0, "NO DATA"),
#     (1, "REQUIRES VENTILATOR"),
#     (2, "WORSE"),
#     (3, "STATUS QUO"),
#     (4, "BETTER"),
# ]

CURRENT_HEALTH_CHOICES = namedtuple(
    'type', ["ND", "RV", "WR", "SQ", "BT"])(0, 1, 2, 3, 4)


CATEGORY_CHOICES = [
    ("Mild", "Category-A"),
    ("Moderate", "Category-B"),
    ("Severe", "Category-C"),
    (None, "UNCLASSIFIED"),
]

# SYMPTOM_CHOICES = [
#     (constants.SYMPTOM_CHOICES.AS, "ASYMPTOMATIC"),
#     (constants.SYMPTOM_CHOICES.FV, "FEVER"),
#     (constants.SYMPTOM_CHOICES.ST, "SORE THROAT"),
#     (constants.SYMPTOM_CHOICES.CO, "COUGH"),
#     (constants.SYMPTOM_CHOICES.BT, "BREATHLESSNESS"),
#     (constants.SYMPTOM_CHOICES.MY, "MYALGIA"),
#     (constants.SYMPTOM_CHOICES.AD, "ABDOMINAL DISCOMFORT"),
#     (constants.SYMPTOM_CHOICES.VD, "VOMITING/DIARRHOEA"),
#     (constants.SYMPTOM_CHOICES.OT, "OTHERS"),
#     (constants.SYMPTOM_CHOICES.SA, "SARI"),
#     (constants.SYMPTOM_CHOICES.SP, "SPUTUM"),
#     (constants.SYMPTOM_CHOICES.NA, "NAUSEA"),
#     (constants.SYMPTOM_CHOICES.CP, "CHEST PAIN"),
#     (constants.SYMPTOM_CHOICES.HP, "HEMOPTYSIS"),
#     (constants.SYMPTOM_CHOICES.ND, "NASAL DISCHARGE"),
#     (constants.SYMPTOM_CHOICES.BA, "BODY ACHE"),
# ]

SYMPTOM_TYPE_CHOICES = namedtuple(
    'type', ["AS", "FV", "ST", "CO", "BT","MY","AD","VD","OT","SA","SP","NA","CP","HP","ND","BA"])(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16)

SYMPTOM_CHOICES = [
    (SYMPTOM_TYPE_CHOICES.AS, "ASYMPTOMATIC"),
    (SYMPTOM_TYPE_CHOICES.FV, "FEVER"),
    (SYMPTOM_TYPE_CHOICES.ST, "SORE THROAT"),
    (SYMPTOM_TYPE_CHOICES.CO, "COUGH"),
    (SYMPTOM_TYPE_CHOICES.BT, "BREATHLESSNESS"),
    (SYMPTOM_TYPE_CHOICES.MY, "MYALGIA"),
    (SYMPTOM_TYPE_CHOICES.AD, "ABDOMINAL DISCOMFORT"),
    (SYMPTOM_TYPE_CHOICES.VD, "VOMITING/DIARRHOEA"),
    (SYMPTOM_TYPE_CHOICES.OT, "OTHERS"),
    (SYMPTOM_TYPE_CHOICES.SA, "SARI"),
    (SYMPTOM_TYPE_CHOICES.SP, "SPUTUM"),
    (SYMPTOM_TYPE_CHOICES.NA, "NAUSEA"),
    (SYMPTOM_TYPE_CHOICES.CP, "CHEST PAIN"),
    (SYMPTOM_TYPE_CHOICES.HP, "HEMOPTYSIS"),
    (SYMPTOM_TYPE_CHOICES.ND, "NASAL DISCHARGE"),
    (SYMPTOM_TYPE_CHOICES.BA, "BODY ACHE"),
]

# DISEASE_CHOICES_MAP = {
#     "NO": 1,
#     "Diabetes": 2,
#     "Heart Disease": 3,
#     "HyperTension": 4,
#     "Kidney Diseases": 5,
#     "Lung Diseases/Asthma": 6,
#     "Cancer": 7,
# }

DISEASE_CHOICES_MAP = namedtuple(
    'type', ["NO", "DB", "HD", "HT", "KD", "LA","CA"])(1, 2, 3, 4, 5, 6, 7)

DISEASE_CHOICES = [
        (DISEASE_CHOICES_MAP.NO, "NO DISEASE"),
        (DISEASE_CHOICES_MAP.DB, "DIABETES"),
        (DISEASE_CHOICES_MAP.HD, "HEART DISEASE"),
        (DISEASE_CHOICES_MAP.HT, "HYPERTENSION"),
        (DISEASE_CHOICES_MAP.KD, "KIDNEY DISEASES"),
        (DISEASE_CHOICES_MAP.LA, "LUNG DISEASES/ASTHMA"),
        (DISEASE_CHOICES_MAP.CA, "CANCER"),
    ]

# DISEASE_CHOICES = [(v, k) for k, v in DISEASE_CHOICES_MAP.items()]

SuggestionChoices = SimpleNamespace(HI="HI", A="A", R="R")

SUGGESTION_CHOICES = [
        (SuggestionChoices.HI, "HOME ISOLATION"),
        (SuggestionChoices.A, "ADMISSION"),
        (SuggestionChoices.R, "REFERRAL"),
]

# SUGGESTION_CHOICES = namedtuple(
#     'type', ["HI", "A", "R"])("HOME ISOLATION","ADMISSION","REFERRAL")

# ADMIT_CHOICES = [
#     (None, "Not admitted"),
#     (1, "Isolation Room"),
#     (2, "ICU"),
#     (3, "ICU with Ventilator"),
#     (20, "Home Isolation"),
#     ]    

ADMIT_CHOICES = namedtuple(
    'type', ["NA", "IR", "ICU", "ICV", "HI"])(None, 1, 2, 3, 20)

SAMPLE_TYPE_CHOICES = namedtuple(
    'type', ["UN", "BA", "TS", "BE", "AS","CS","OT"])(0, 1, 2, 3, 4, 5, 6)
# SAMPLE_TYPE_CHOICES = [
#     (0, "UNKNOWN"),
#     (1, "BA/ETA"),
#     (2, "TS/NPS/NS"),
#     (3, "Blood in EDTA"),
#     (4, "Acute Sera"),
#     (5, "Covalescent sera"),
#     (6, "OTHER TYPE"),
#     ]

SAMPLE_TEST_RESULT_MAP = namedtuple(
    'type', ["P", "N", "A","I"])(1, 2, 3, 4)

# SAMPLE_TEST_RESULT_CHOICES = [
#     (constants.SAMPLE_TEST_RESULT_MAP.P, 'POSITIVE'),
#     (constants.SAMPLE_TEST_RESULT_MAP.N, 'NEGATIVE'),
#     (constants.SAMPLE_TEST_RESULT_MAP.A, 'AWAITING'),
#     (constants.SAMPLE_TEST_RESULT_MAP.I, 'INVALID')
# ]

# SAMPLE_TEST_RESULT_MAP = {"POSITIVE": 1, "NEGATIVE": 2, "AWAITING": 3, "INVALID": 4}
# SAMPLE_TEST_RESULT_CHOICES = [(v, k) for k, v in SAMPLE_TEST_RESULT_MAP.items()]

    
SAMPLE_FLOW_RULES = {
    # previous rule      # next valid rules
    "REQUEST_SUBMITTED": {"APPROVED", "DENIED",},
    "APPROVED": {"SENT_TO_COLLECTON_CENTRE", "RECEIVED_AND_FORWARED", "RECEIVED_AT_LAB", "COMPLETED"},
    "DENIED": {"REQUEST_SUBMITTED"},
    "SENT_TO_COLLECTON_CENTRE": {"RECEIVED_AND_FORWARED", "RECEIVED_AT_LAB", "COMPLETED"},
    "RECEIVED_AND_FORWARED": {"RECEIVED_AT_LAB", "COMPLETED"},
    "RECEIVED_AT_LAB": {"COMPLETED"},
}

SAMPLE_TEST_FLOW_MAP = namedtuple(
    'type', ["RS", "AP", "DN", "SC", "RF","RL","CT"])(1, 2, 3, 4, 5, 6, 7)

# SAMPLE_TEST_FLOW_MAP = {
#         "REQUEST_SUBMITTED": 1,
#         "APPROVED": 2,
#         "DENIED": 3,
#         "SENT_TO_COLLECTON_CENTRE": 4,
#         "RECEIVED_AND_FORWARED": 5,
#         "RECEIVED_AT_LAB": 6,
#         "COMPLETED": 7,
#     }

SAMPLE_TEST_FLOW_CHOICES = [
    (SAMPLE_TEST_FLOW_MAP.RS, 'REQUEST_SUBMITTED'),
    (SAMPLE_TEST_FLOW_MAP.AP, 'APPROVED'),
    (SAMPLE_TEST_FLOW_MAP.DN, 'DENIED'),
    (SAMPLE_TEST_FLOW_MAP.SC, 'SENT_TO_COLLECTON_CENTRE'),
    (SAMPLE_TEST_FLOW_MAP.RF, 'RECEIVED_AND_FORWARED'),
    (SAMPLE_TEST_FLOW_MAP.RL, 'RECEIVED_AT_LAB'),
    (SAMPLE_TEST_FLOW_MAP.CT, 'COMPLETED'),
]

# SAMPLE_TEST_FLOW_CHOICES = [(v, k) for k, v in SAMPLE_TEST_FLOW_MAP.items()]    