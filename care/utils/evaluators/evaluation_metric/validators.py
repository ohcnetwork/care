from pydantic import UUID4


def validate_patient_age_equality(value):
    if not isinstance(value, (int, float)):
        raise ValueError("patient_age equality operation requires an numeric value")


def validate_patient_age_in_range(value):
    if not isinstance(value, dict):
        raise ValueError("patient_age in_range operation requires a dictionary value")
    if "min" not in value and "max" not in value:
        raise ValueError(
            "patient_age in_range operation requires at least 'min' or 'max' key"
        )
    if (
        "min" in value
        and value["min"] is not None
        and not isinstance(value["min"], (int, float))
    ):
        raise ValueError("patient_age 'min' value must be a number")
    if (
        "max" in value
        and value["max"] is not None
        and not isinstance(value["max"], (int, float))
    ):
        raise ValueError("patient_age 'max' value must be a number")
    if (
        "min" in value
        and "max" in value
        and value["min"] is not None
        and value["max"] is not None
        and value["min"] > value["max"]
    ):
        raise ValueError("patient_age 'min' value cannot be greater than 'max' value")


def validate_patient_gender_equality(value):
    if not isinstance(value, str):
        raise ValueError("patient_gender equality operation requires a string value")
    if not value.strip():
        raise ValueError(
            "patient_gender equality operation requires a non-empty string value"
        )


def validate_encounter_tag_has_tag(value):
    try:
        UUID4(value)
    except ValueError as err:
        raise ValueError(
            "encounter_tag has_tag operation requires a valid UUID string"
        ) from err
