import collections

GENDERS = collections.namedtuple("GENDERS", ["MALE", "FEMALE", "NON_BINARY"])(MALE=1, FEMALE=2, NON_BINARY=3,)

GENDER_CHOICES = (
    (GENDERS.MALE, "Male"),
    (GENDERS.FEMALE, "Female"),
    (GENDERS.NON_BINARY, "Non-binary"),
)

FIELDS_CHARACTER_LIMITS = {"NAME": 255, "PHONE_NUMBER": 14, "LOCALBODY_CODE": 20}


# User Type Constants
FACILITY_MANAGER = "Facility Manager"
MANAGER = "District Manager"
PORTEA = "Portea"
