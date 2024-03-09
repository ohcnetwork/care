import enum
from types import SimpleNamespace

from django.db.models import IntegerChoices, TextChoices
from django.utils.translation import gettext_lazy as _


def reverse_choices(choices):
    output = {}
    for choice in choices:
        output[choice[0]] = choice[1]
    return output

#
# def reverse_choices_class(choices_class):
#     output = {}
#     for choice in choices_class:
#         output[choice.value] = choice.label
#     return output


# CURRENT_HEALTH_CHOICES = [
#     (0, "NO DATA"),
#     (1, "REQUIRES VENTILATOR"),
#     (2, "WORSE"),
#     (3, "STATUS QUO"),
#     (4, "BETTER"),
# ]

class CurrentHealthChoices(IntegerChoices):
    NO_DATA = 0, _("No Data")
    REQUIRES_VENTILATOR = 1, _("Requires Ventilator")
    WORSE = 2, _("Worse")
    STATUS_QUO = 3, _("Status Quo")
    BETTER = 4, _("Better")


# SYMPTOM_CHOICES = [
#     (1, "ASYMPTOMATIC"),
#     (2, "FEVER"),
#     (3, "SORE THROAT"),
#     (4, "COUGH"),
#     (5, "BREATHLESSNESS"),
#     (6, "MYALGIA"),
#     (7, "ABDOMINAL DISCOMFORT"),
#     (8, "VOMITING"),
#     (9, "OTHERS"),
#     (11, "SPUTUM"),
#     (12, "NAUSEA"),
#     (13, "CHEST PAIN"),
#     (14, "HEMOPTYSIS"),
#     (15, "NASAL DISCHARGE"),
#     (16, "BODY ACHE"),
#     (17, "DIARRHOEA"),
#     (18, "PAIN"),
#     (19, "PEDAL EDEMA"),
#     (20, "WOUND"),
#     (21, "CONSTIPATION"),
#     (22, "HEAD ACHE"),
#     (23, "BLEEDING"),
#     (24, "DIZZINESS"),
#     (25, "CHILLS"),
#     (26, "GENERAL WEAKNESS"),
#     (27, "IRRITABILITY"),
#     (28, "CONFUSION"),
#     (29, "ABDOMINAL PAIN"),
#     (30, "JOINT PAIN"),
#     (31, "REDNESS OF EYES"),
#     (32, "ANOREXIA"),
#     (33, "NEW LOSS OF TASTE"),
#     (34, "NEW LOSS OF SMELL"),
# ]


class SymptomChoices(IntegerChoices):
    ASYMPTOMATIC = 1, _("Asymptomatic")
    FEVER = 2, _("Fever")
    SORE_THROAT = 3, _("Sore Throat")
    COUGH = 4, _("Cough")
    BREATHLESSNESS = 5, _("Breathlessness")
    MYALGIA = 6, _("Myalgia")
    ABDOMINAL_DISCOMFORT = 7, _("Abdominal Discomfort")
    VOMITING = 8, _("Vomiting")
    OTHERS = 9, _("Others")
    SPUTUM = 11, _("Sputum")
    NAUSEA = 12, _("Nausea")
    CHEST_PAIN = 13, _("Chest Pain")
    HEMOPTYSIS = 14, _("Hemoptysis")
    NASAL_DISCHARGE = 15, _("Nasal Discharge")
    BODY_ACHE = 16, _("Body Ache")
    DIARRHOEA = 17, _("Diarrhoea")
    PAIN = 18, _("Pain")
    PEDAL_EDEMA = 19, _("Pedal Edema")
    WOUND = 20, _("Wound")
    CONSTIPATION = 21, _("Constipation")
    HEAD_ACHE = 22, _("Head Ache")
    BLEEDING = 23, _("Bleeding")
    DIZZINESS = 24, _("Dizziness")
    CHILLS = 25, _("Chills")
    GENERAL_WEAKNESS = 26, _("General Weakness")
    IRRITABILITY = 27, _("Irritability")
    CONFUSION = 28, _("Confusion")
    ABDOMINAL_PAIN = 29, _("Abdominal Pain")
    JOINT_PAIN = 30, _("Joint Pain")
    REDNESS_OF_EYES = 31, _("Redness of Eyes")
    ANOREXIA = 32, _("Anorexia")
    NEW_LOSS_OF_TASTE = 33, _("New Loss of Taste")
    NEW_LOSS_OF_SMELL = 34, _("New Loss of Smell")


# DISEASE_CHOICES_MAP = {
#     "NO": 1,
#     "Diabetes": 2,
#     "Heart Disease": 3,
#     "HyperTension": 4,
#     "Kidney Diseases": 5,
#     "Lung Diseases/Asthma": 6,
#     "Cancer": 7,
#     "OTHER": 8,
# }
# DISEASE_CHOICES = [(v, k) for k, v in DISEASE_CHOICES_MAP.items()]
#
# COVID_CATEGORY_CHOICES = [
#     ("ASYM", "ASYMPTOMATIC"),
#     ("Mild", "Category-A"),
#     ("Moderate", "Category-B"),
#     ("Severe", "Category-C"),
#     (None, "UNCLASSIFIED"),
# ]  # Deprecated

# CATEGORY_CHOICES = [
#     ("Comfort", "Comfort Care"),
#     ("Stable", "Stable"),
#     ("Moderate", "Abnormal"),
#     ("Critical", "Critical"),
# ]
#
# DISCHARGE_REASON_CHOICES = [
#     ("REC", "Recovered"),
#     ("REF", "Referred"),
#     ("EXP", "Expired"),
#     ("LAMA", "LAMA"),
# ]

class DiseaseChoices(IntegerChoices):
    NO = 1, _("No")
    DIABETES = 2, _("Diabetes")
    HEART_DISEASE = 3, _("Heart Disease")
    HYPERTENSION = 4, _("HyperTension")
    KIDNEY_DISEASES = 5, _("Kidney Diseases")
    LUNG_DISEASES_ASTHMA = 6, _("Lung Diseases/Asthma")
    CANCER = 7, _("Cancer")
    OTHER = 8, _("Other")


DISEASE_CHOICES_MAP = {choice.label: choice.value for choice in DiseaseChoices}


class CovidCategoryChoices(TextChoices): # Deprecated
    ASYM = "ASYM", _("Asymptomatic")
    MILD = "Mild", _("Category-A")
    MODERATE = "Moderate", _("Category-B")
    SEVERE = "Severe", _("Category-C")
    UNCLASSIFIED = None, _("Unclassified")


class CategoryChoices(TextChoices):
    COMFORT = "Comfort", _("Comfort Care")
    STABLE = "Stable", _("Stable")
    MODERATE = "Moderate", _("Abnormal")
    CRITICAL = "Critical", _("Critical")


class DischargeReasonChoices(TextChoices):
    REC = "REC", _("Recovered")
    REF = "REF", _("Referred")
    EXP = "EXP", _("Expired")
    LAMA = "LAMA", _("LAMA")


# class NewDischargeReasonEnum(IntegerChoices):
#     UNKNOWN = -1, _("Unknown")
#     RECOVERED = 1, _("Recovered")
#     REFERRED = 2, _("Referred")
#     EXPIRED = 3, _("Expired")
#     LAMA = 4, _("LAMA")
#
#
# NEW_DISCHARGE_REASON_CHOICES = [(e.value, e.name) for e in NewDischargeReasonEnum]

class NewDischargeReasons(IntegerChoices):
    UNKNOWN = -1, _("Unknown")
    RECOVERED = 1, _("Recovered")
    REFERRED = 2, _("Referred")
    EXPIRED = 3, _("Expired")
    LAMA = 4, _("LAMA")


#
# class DiseaseStatusEnum(enum.IntEnum):
#     SUSPECTED = 1
#     POSITIVE = 2
#     NEGATIVE = 3
#     RECOVERY = 4
#     RECOVERED = 5
#     EXPIRED = 6
#
#
# DISEASE_STATUS_CHOICES = [(e.value, e.name) for e in DiseaseStatusEnum]

# DISEASE_STATUS_DICT = {}                                #
# for i in DISEASE_STATUS_CHOICES:
#     DISEASE_STATUS_DICT[i[1]] = i[0]

# BLOOD_GROUP_CHOICES = [
#     ("A+", "A+"),
#     ("A-", "A-"),
#     ("B+", "B+"),
#     ("B-", "B-"),
#     ("AB+", "AB+"),
#     ("AB-", "AB-"),
#     ("O+", "O+"),
#     ("O-", "O-"),
#     ("UNK", "UNKNOWN"),
# ]

class DiseaseStatus(IntegerChoices):
    SUSPECTED = 1, _("Suspected")
    POSITIVE = 2, _("Positive")
    NEGATIVE = 3, _("Negative")
    RECOVERY = 4, _("Recovery")
    RECOVERED = 5, _("Recovered")
    EXPIRED = 6, _("Expired")


class BloodGroupChoices(TextChoices):
    A_POSITIVE = "A+", _("A+")
    A_NEGATIVE = "A-", _("A-")
    B_POSITIVE = "B+", _("B+")
    B_NEGATIVE = "B-", _("B-")
    AB_POSITIVE = "AB+", _("AB+")
    AB_NEGATIVE = "AB-", _("AB-")
    O_POSITIVE = "O+", _("O+")
    O_NEGATIVE = "O-", _("O-")
    UNKNOWN = "UNK", _("Unknown")


SuggestionChoices = SimpleNamespace(HI="HI", A="A", R="R", OP="OP", DC="DC", DD="DD")


class RouteToFacility(IntegerChoices):
    OUTPATIENT = 10, _("Outpatient/Emergency Room")
    INTER_FACILITY_TRANSFER = 20, _("Referred from another facility")
    INTRA_FACILITY_TRANSFER = 30, _("Internal Transfer within the facility")
    __empty__ = _("(Unknown)")


# class BedType(enum.Enum):
#     ISOLATION = 1
#     ICU = 2
#     ICU_WITH_NON_INVASIVE_VENTILATOR = 3
#     ICU_WITH_OXYGEN_SUPPORT = 4
#     ICU_WITH_INVASIVE_VENTILATOR = 5
#     BED_WITH_OXYGEN_SUPPORT = 6
#     REGULAR = 7
#
#
# BedTypeChoices = [(e.value, e.name) for e in BedType]

class BedTypeChoices(IntegerChoices):
    ISOLATION = 1, _('Isolation')
    ICU = 2, _('ICU')
    ICU_WITH_NON_INVASIVE_VENTILATOR = 3, _('ICU with Non-Invasive Ventilator')
    ICU_WITH_OXYGEN_SUPPORT = 4, _('ICU with Oxygen Support')
    ICU_WITH_INVASIVE_VENTILATOR = 5, _('ICU with Invasive Ventilator')
    BED_WITH_OXYGEN_SUPPORT = 6, _('Bed with Oxygen Support')
    REGULAR = 7, _('Regular')


# REVERSE_BLOOD_GROUP_CHOICES = reverse_choices(BLOOD_GROUP_CHOICES)
# REVERSE_DISEASE_STATUS_CHOICES = reverse_choices(DISEASE_STATUS_CHOICES)
# REVERSE_COVID_CATEGORY_CHOICES = reverse_choices_class(CovidCategoryChoices)  # Deprecated
# REVERSE_CATEGORY_CHOICES = reverse_choices(CATEGORY_CHOICES)
# REVERSE_BED_TYPE_CHOICES = reverse_choices_class(BedTypeChoices)
# REVERSE_ROUTE_TO_FACILITY_CHOICES = reverse_choices(RouteToFacility.choices)
# REVERSE_DISCHARGE_REASON_CHOICES = reverse_choices(DISCHARGE_REASON_CHOICES)
# REVERSE_NEW_DISCHARGE_REASON_CHOICES = reverse_choices(NEW_DISCHARGE_REASON_CHOICES)
