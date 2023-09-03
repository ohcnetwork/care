from django.db.models import CharField, TextField, Value
from django.db.models.functions import Coalesce

from care.facility.models.prescription import MedibaseMedicine


def load_medibase_in_memory():
    return (
        MedibaseMedicine.objects.all()
        .annotate(
            generic_pretty=Coalesce("generic", Value(""), output_field=CharField()),
            company_pretty=Coalesce("company", Value(""), output_field=CharField()),
            contents_pretty=Coalesce("contents", Value(""), output_field=TextField()),
            cims_class_pretty=Coalesce(
                "cims_class",
                Value(""),
                output_field=CharField(),
            ),
            atc_classification_pretty=Coalesce(
                "atc_classification",
                Value(""),
                output_field=TextField(),
            ),
        )
        .values_list(
            "external_id",
            "name",
            "type",
            "generic_pretty",
            "company_pretty",
            "contents_pretty",
            "cims_class_pretty",
            "atc_classification_pretty",
        )
    )


MedibaseMedicineTable = load_medibase_in_memory()
