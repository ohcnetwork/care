from littletable import Table

from care.facility.models.prescription import MedibaseMedicine

MedibaseMedicineTable = Table("MedibaseMedicine")

medibase_objects = MedibaseMedicine.objects.all()

for obj in medibase_objects:
    MedibaseMedicineTable.insert(
        {
            "id": obj.id,
            "external_id": obj.external_id,
            "name": obj.name,
            "type": obj.type,
            "generic": obj.generic or "",
            "company": obj.company or "",
            "contents": obj.contents or "",
            "cims_class": obj.cims_class or "",
            "atc_classification": obj.atc_classification or "",
            "searchable": f"{obj.name} {obj.generic} {obj.company}",
        }
    )

MedibaseMedicineTable.create_index("id", unique=True)
MedibaseMedicineTable.create_search_index("searchable")
