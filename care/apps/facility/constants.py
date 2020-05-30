from collections import namedtuple

ROOM_TYPES_CHOICES = namedtuple(
    "ROOM_TYPES_CHOICES",
    [
        "TOTAL",
        "GENERAL_BED",
        "HOSTEL",
        "SINGLE_ROOM_WITH_ATTACHED_BATHROOM",
        "ICU",
        "VENTILATOR",
    ],
)(0, 1, 2, 3, 10, 20)

ROOM_TYPES = [
    (ROOM_TYPES_CHOICES.TOTAL, "Total"),
    (ROOM_TYPES_CHOICES.GENERAL_BED, "General Bed"),
    (ROOM_TYPES_CHOICES.HOSTEL, "Hostel"),
    (
        ROOM_TYPES_CHOICES.SINGLE_ROOM_WITH_ATTACHED_BATHROOM,
        "Single Room with Attached Bathroom",
    ),
    (ROOM_TYPES_CHOICES.ICU, "ICU"),
    (ROOM_TYPES_CHOICES.VENTILATOR, "Ventilator"),
]

FACILITY_TYPES_CHOICES = namedtuple(
    "FACILITY_TYPES_CHOICES",
    [
        "EDUCATIONAL_INST",
        "PRIVATE_HOSPITAL",
        "OTHER",
        "HOSTEL",
        "HOTEL",
        "LODGE",
        "TELEMEDICINE",
        "GOVT_HOSPITAL",
        "LABS",
        "PRIMARY_HEALTH_CENTRES",
        "ALL_DAY_PUBLIC_HEALTH_CENTRES",
        "FAMILY_HEALTH_CENTRES",
        "COMMUNITY_HEALTH_CENTRES",
        "URBAN_PRIMARY_HEALTH_CENTER",
        "TALUK_HOSPITALS",
        "TALUK_HEADQUARTERS_HOSPITALS",
        "WOMEN_AND_CHILD_HEALTH_CENTRES",
        "GENERAL_HOSPITALS",
        "DISTRICT_HOSPITALS",
        "GOVT_MEDICAL_COLLEGE_HOSPITALS",
        "CORONA_TESTING_LABS",
        "CORONA_CARE_CENTRE",
    ],
)(
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    800,
    801,
    802,
    803,
    820,
    830,
    831,
    840,
    850,
    860,
    870,
    950,
    1000,
)

FACILITY_TYPES = [
    (FACILITY_TYPES_CHOICES.EDUCATIONAL_INST, "Educational Inst"),
    (FACILITY_TYPES_CHOICES.PRIVATE_HOSPITAL, "Private Hospital"),
    (FACILITY_TYPES_CHOICES.OTHER, "Other"),
    (FACILITY_TYPES_CHOICES.HOSTEL, "Hostel"),
    (FACILITY_TYPES_CHOICES.HOTEL, "Hotel"),
    (FACILITY_TYPES_CHOICES.LODGE, "Lodge"),
    (FACILITY_TYPES_CHOICES.TELEMEDICINE, "TeleMedicine"),
    (FACILITY_TYPES_CHOICES.GOVT_HOSPITAL, "Govt Hospital"),
    (FACILITY_TYPES_CHOICES.LABS, "Labs"),
    # Use 8xx for Govt owned hospitals and health centres
    (FACILITY_TYPES_CHOICES.PRIMARY_HEALTH_CENTRES, "Primary Health Centres"),
    (
        FACILITY_TYPES_CHOICES.ALL_DAY_PUBLIC_HEALTH_CENTRES,
        "24x7 Public Health Centres",
    ),
    (FACILITY_TYPES_CHOICES.FAMILY_HEALTH_CENTRES, "Family Health Centres"),
    (FACILITY_TYPES_CHOICES.COMMUNITY_HEALTH_CENTRES, "Community Health Centres"),
    (FACILITY_TYPES_CHOICES.URBAN_PRIMARY_HEALTH_CENTER, "Urban Primary Health Center"),
    (FACILITY_TYPES_CHOICES.TALUK_HOSPITALS, "Taluk Hospitals"),
    (
        FACILITY_TYPES_CHOICES.TALUK_HEADQUARTERS_HOSPITALS,
        "Taluk Headquarters Hospitals",
    ),
    (
        FACILITY_TYPES_CHOICES.WOMEN_AND_CHILD_HEALTH_CENTRES,
        "Women and Child Health Centres",
    ),
    (
        FACILITY_TYPES_CHOICES.GENERAL_HOSPITALS,
        "General hospitals",
    ),  # TODO: same as 8, need to merge
    (FACILITY_TYPES_CHOICES.DISTRICT_HOSPITALS, "District Hospitals"),
    (
        FACILITY_TYPES_CHOICES.GOVT_MEDICAL_COLLEGE_HOSPITALS,
        "Govt Medical College Hospitals",
    ),
    # Use 9xx for Labs
    (FACILITY_TYPES_CHOICES.CORONA_TESTING_LABS, "Corona Testing Labs"),
    # Use 10xx for Corona Care Center
    (FACILITY_TYPES_CHOICES.CORONA_CARE_CENTRE, "Corona Care Centre"),
]

LAB_OWNERSHIP_CHOICES = namedtuple("LAB_OWNERSHIP_CHOICES", ["GOVERNMENT", "PRIVATE"])(
    1, 2
)

DOCTOR_TYPES_CHOICES = namedtuple(
    "DOCTOR_TYPES_CHOICES",
    [
        "GENERAL_MEDICINE",
        "PULMONOLOGY",
        "CRITICAL_CARE",
        "PAEDIATRICS",
        "OTHER_SPECIALITY",
    ],
)(1, 2, 3, 4, 5)

DOCTOR_TYPES = [
    (DOCTOR_TYPES_CHOICES.GENERAL_MEDICINE, "General Medicine"),
    (DOCTOR_TYPES_CHOICES.PULMONOLOGY, "Pulmonology"),
    (DOCTOR_TYPES_CHOICES.CRITICAL_CARE, "Critical Care"),
    (DOCTOR_TYPES_CHOICES.PAEDIATRICS, "Paediatrics"),
    (DOCTOR_TYPES_CHOICES.OTHER_SPECIALITY, "Other Speciality"),
]

AMBULANCE_TYPES_CHOICES = namedtuple(
    "AMBULANCE_TYPES_CHOICES", ["BASIC", "CARDIAC", "HEARSE",]
)(1, 2, 3)

AMBULANCE_TYPES = [
    (AMBULANCE_TYPES_CHOICES.BASIC, "Basic"),
    (AMBULANCE_TYPES_CHOICES.CARDIAC, "Cardiac"),
    (AMBULANCE_TYPES_CHOICES.HEARSE, "Hearse"),
]

INSURANCE_YEAR_CHOICES = ((2020, 2020), (2021, 2021), (2022, 2022))

LAB_TYPE_CHOICES = namedtuple(
    "LAB_TYPE_CHOICES", ["AC", "BC", "DI", "HT", "KT", "TT", "UL"]
)(1, 2, 3, 4, 5, 6, 7)
