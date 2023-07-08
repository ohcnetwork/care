from care.facility.models.prescription import MedibaseMedicine

medibase_objects = MedibaseMedicine.objects.all()

MedibaseMedicineTable = tuple(
    (
        obj.external_id,
        obj.name,
        obj.type,
        obj.generic or "",
        obj.company or "",
        obj.contents or "",
        obj.cims_class or "",
        obj.atc_classification or "",
    )
    for obj in medibase_objects
)


# for obj in medibase_objects:
# MedibaseMedicineTable.append(
#     {
#         "external_id": obj.external_id,
#         "name": obj.name,
#         "type": obj.type,
#         "generic": obj.generic or "",
#         "company": obj.company or "",
#         "contents": obj.contents or "",
#         "cims_class": obj.cims_class or "",
#         "atc_classification": obj.atc_classification or "",
#     }
# )
