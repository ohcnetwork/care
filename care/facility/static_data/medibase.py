from care.facility.models.prescription import MedibaseMedicine


def load_medibase_in_memory():
    medibase_objects = MedibaseMedicine.objects.all()
    return tuple(
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


MedibaseMedicineTable = load_medibase_in_memory()
