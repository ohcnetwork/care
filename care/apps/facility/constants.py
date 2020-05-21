ROOM_TYPES = [
    (0, "Total"),
    (1, "General Bed"),
    (2, "Hostel"),
    (3, "Single Room with Attached Bathroom"),
    (10, "ICU"),
    (20, "Ventilator"),
]

FACILITY_TYPES = [
    (1, "Educational Inst"),
    (2, "Private Hospital"),
    (3, "Other"),
    (4, "Hostel"),
    (5, "Hotel"),
    (6, "Lodge"),
    (7, "TeleMedicine"),
    (8, "Govt Hospital"),
    (9, "Labs"),
    # Use 8xx for Govt owned hospitals and health centres
    (800, "Primary Health Centres"),
    (801, "24x7 Public Health Centres"),
    (802, "Family Health Centres"),
    (803, "Community Health Centres"),
    (820, "Urban Primary Health Center"),
    (830, "Taluk Hospitals"),
    (831, "Taluk Headquarters Hospitals"),
    (840, "Women and Child Health Centres"),
    (850, "General hospitals"),  # TODO: same as 8, need to merge
    (860, "District Hospitals"),
    (870, "Govt Medical College Hospitals"),
    # Use 9xx for Labs
    (950, "Corona Testing Labs"),
    # Use 10xx for Corona Care Center
    (1000, "Corona Care Centre"),
]

DOCTOR_TYPES = [
    (1, "General Medicine"),
    (2, "Pulmonology"),
    (3, "Critical Care"),
    (4, "Paediatrics"),
    (5, "Other Speciality"),
]

AMBULANCE_TYPES = [
    (1, "Basic"), 
    (2, "Cardiac"), 
    (3, "Hearse")
]
