from django.db import models


def validate_associating_id(
    associating_model: type[models.Model],
    associating_id: str,
    report_type_key: str,
) -> models.Model:
    return associating_model.objects.get(external_id=associating_id)
