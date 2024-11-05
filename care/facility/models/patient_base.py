from types import SimpleNamespace

from django.db.models import IntegerChoices, TextChoices
from django.utils.translation import gettext_lazy as _


def reverse_choices(choices):
    output = {}
    for choice in choices:
        output[choice[0]] = choice[1]
    return output


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


class DiseaseChoices(IntegerChoices):
    NO = 1, _("No")
    DIABETES = 2, _("Diabetes")
    HEART_DISEASE = 3, _("Heart Disease")
    HYPERTENSION = 4, _("Hypertension")
    KIDNEY_DISEASES = 5, _("Kidney Diseases")
    LUNG_DISEASES_ASTHMA = 6, _("Lung Diseases/Asthma")
    CANCER = 7, _("Cancer")
    OTHER = 8, _("Other")


COVID_CATEGORY_CHOICES = [
    ("ASYM", "ASYMPTOMATIC"),
    ("Mild", "Category-A"),
    ("Moderate", "Category-B"),
    ("Severe", "Category-C"),
    (None, "UNCLASSIFIED"),
]  # Deprecated


class CategoryChoices(TextChoices):
    COMFORT = "Comfort", _("Comfort Care")
    STABLE = "Stable", _("Mild")
    MODERATE = "Moderate", _("Moderate")
    CRITICAL = "Critical", _("Critical")
    ACTIVELY_DYING = "ActivelyDying", _("Actively Dying")


DISCHARGE_REASON_CHOICES = [
    ("REC", "Recovered"),
    ("REF", "Referred"),
    ("EXP", "Expired"),
    ("LAMA", "LAMA"),
]


class NewDischargeReasonChoices(IntegerChoices):
    UNKNOWN = -1, _("Unknown")
    RECOVERED = 1, _("Recovered")
    REFERRED = 2, _("Referred")
    EXPIRED = 3, _("Expired")
    LAMA = 4, _("LAMA")


class DiseaseStatusChoices(IntegerChoices):
    SUSPECTED = 1, _("Suspected")
    POSITIVE = 2, _("Positive")
    NEGATIVE = 3, _("Negative")
    RECOVERY = 4, _("Recovery")
    RECOVERED = 5, _("Recovered")
    EXPIRED = 6, _("Expired")


DISEASE_STATUS_DICT = {choice.name: choice.value for choice in DiseaseStatusChoices}


class BloodGroupChoices(TextChoices):
    A_POS = "A+", _("A+")
    A_NEG = "A-", _("A-")
    B_POS = "B+", _("B+")
    B_NEG = "B-", _("B-")
    AB_POS = "AB+", _("AB+")
    AB_NEG = "AB-", _("AB-")
    O_POS = "O+", _("O+")
    O_NEG = "O-", _("O-")
    UNKNOWN = "UNK", _("Unknown")


SuggestionChoices = SimpleNamespace(HI="HI", A="A", R="R", OP="OP", DC="DC", DD="DD")


class RouteToFacility(IntegerChoices):
    OUTPATIENT = 10, _("Outpatient/Emergency Room")
    INTER_FACILITY_TRANSFER = 20, _("Referred from another facility")
    INTRA_FACILITY_TRANSFER = 30, _("Internal Transfer within the facility")
    __empty__ = _("(Unknown)")


class BedTypeChoices(IntegerChoices):
    ISOLATION = 1, _("Isolation")
    ICU = 2, _("ICU")
    ICU_WITH_NON_INVASIVE_VENTILATOR = 3, _("ICU with Non-Invasive Ventilator")
    ICU_WITH_OXYGEN_SUPPORT = 4, _("ICU with Oxygen Support")
    ICU_WITH_INVASIVE_VENTILATOR = 5, _("ICU with Invasive Ventilator")
    BED_WITH_OXYGEN_SUPPORT = 6, _("Bed with Oxygen Support")
    REGULAR = 7, _("Regular")


REVERSE_COVID_CATEGORY_CHOICES = reverse_choices(COVID_CATEGORY_CHOICES)  # Deprecated
REVERSE_DISCHARGE_REASON_CHOICES = reverse_choices(DISCHARGE_REASON_CHOICES)
