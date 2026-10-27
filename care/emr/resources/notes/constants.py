from enum import Enum


class NoteThreadType(str, Enum):
    patient = "patient"
    referral = "referral"
