DOCTOR = 1
STAFF = 2
PATIENT = 3
VOLUNTEER = 4
DISTRICT_LAB_ADMIN = 5
DISTRICT_ADMIN = 6
STATE_LAB_ADMIN = 7
STATE_ADMIN = 8

USER_TYPE_VALUES = (
    (DOCTOR, 'Doctor'),
    (STAFF, 'Staff'),
    (PATIENT, 'Patient'),
    (DISTRICT_LAB_ADMIN, 'DistrictLabAdmin'),
    (DISTRICT_ADMIN, 'DistrictAdmin'),
    (STATE_LAB_ADMIN, 'StateLabAdmin'),
    (STATE_ADMIN, 'StateAdmin'),
)

GRAM_PANCHAYATH = 1
BLOCK_PANCHAYATH = 2
DISTRICT_PANCHAYATH = 3
MUNICIPALITY = 10
CORPORATION = 20
OTHERS = 50

LOCAL_BODY_CHOICES = (
    (GRAM_PANCHAYATH, 'Gram Panchayath'),
    (BLOCK_PANCHAYATH, 'Block Panchayath'),
    (DISTRICT_PANCHAYATH, 'District Panchayath'),
    (MUNICIPALITY, 'Municipality'),
    (CORPORATION, 'Corporation'),
    (OTHERS, 'Others'),
)
