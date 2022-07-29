from care.users.models import District
from care.facility.models import Ambulance

ambulances = [
    {
        "vehicle_number": "KL03AG2430",
        "owner_name": "Amitabh Nanda",
        "owner_phone_number": "+919090909090",
        "owner_is_smart_phone": True,
        "primary_district": 1,
        "secondary_district": None,
        "third_district": None,
        "has_oxygen": False,
        "has_ventilator": False,
        "has_suction_machine": False,
        "has_defibrillator": False,
        "insurance_valid_till_year": 2022,
        "ambulance_type": 2,
        "price_per_km": "10.00",
        "has_free_service": False
    }
]

ambulance_drivers = [
    {
        "ambulance": Ambulance.objects.get(vehicle_number="KL03AG2430").id,
        "name": "Ramkrishna Pranay",
        "phone_number": "+919090909091",
        "is_smart_phone": True
    },
    {
        "ambulance": Ambulance.objects.get(vehicle_number="KL03AG2430").id,
        "name": "Swarna Krishna",
        "phone_number": "+919090909092",
        "is_smart_phone": True
    },
    {
        "ambulance": Ambulance.objects.get(vehicle_number="KL03AG2430").id,
        "name": "Mitra Jayesh",
        "phone_number": "+919090909093",
        "is_smart_phone": True
    },
]
