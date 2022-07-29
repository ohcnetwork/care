from care.facility.models import Facility

asset_data = [
    {
        "name": "camera for testing",
        "description": "",
        "asset_type": 50,
        "asset_class": None,
        "status": 50,
        "current_location": 1,
        "is_working": None,
        "not_working_reason": None,
        "serial_number": None,
        "warranty_details": "",
        "meta": {},
        "vendor_name": None,
        "support_name": None,
        "support_phone": "+919988778877",
        "support_email": None,
        "qr_code_id": None
    },
    {
        "name": "monitor",
        "description": "",
        "asset_type": 100,
        "asset_class": "",
        "status": 50,
        "current_location": 1,
        "is_working": True,
        "not_working_reason": "",
        "serial_number": None,
        "warranty_details": "",
        "meta": {},
        "vendor_name": None,
        "support_name": None,
        "support_phone": "+919898988888",
        "support_email": None,
        "qr_code_id": None
    },
]

asset_locations = [
    {
        "name": "St George Hospital",
        "description": "",
        "location_type": 10,
        "facility": Facility.objects.get(name="St George Hospital V1").id, 
    }
]
