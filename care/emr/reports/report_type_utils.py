from django.db import models


def validate_associating_id(
    associating_model: type[models.Model],
    associating_id: str,
    report_type_key: str,
    validator_func=None,
) -> models.Model:
    if validator_func:
        return validator_func(associating_id)

    try:
        return associating_model.objects.get(external_id=associating_id)
    except associating_model.DoesNotExist as e:
        msg = (
            f"Invalid associating_id for report type '{report_type_key}': "
            f"{associating_model.__name__} with external_id '{associating_id}' does not exist"
        )
        raise ValueError(msg) from e
    except Exception as e:
        msg = f"Error validating associating_id for report type '{report_type_key}': {e!s}"
        raise ValueError(msg) from e
