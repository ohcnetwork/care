from care.facility.models import Asset, Bed, Facility

beds = [
    {
        "name": "Test Bed",
        "description": "",
        "bed_type": 7,
        "facility": Facility.objects.get(name="St George Hospital V1").id,
        "meta": {},
        "location": 1
    }
]

assetbeds = [
    {
        "asset": Asset.objects.get(name="camera for testing").id,
        "bed": Bed.objects.get(name="Test Bed").id,
        "meta": {}
    }
]
