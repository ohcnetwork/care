"""
This is the base class to create patient identifiers based on patient attributes
This allows workflows without strict Authz to function as needed
"""

from care.emr.models.patient import PatientIdentifier, PatientIdentifierConfig
from care.emr.resources.patient_identifier.spec import (
    IdentifierConfig,
    PatientIdentifierRetrieveConfig,
    PatientIdentifierStatus,
    PatientIdentifierUse,
)


class BasePatientIdentifierConfig:
    IDENTIFIER_SYSTEM = None
    CACHED_CONFIG = {}
    DISPLAY = None
    RETRIEVE_WITH_YOB = None
    PARTIAL_SEARCH = None

    @classmethod
    def get__or_create_system_name_identifier_config(cls):
        if cls.IDENTIFIER_SYSTEM in cls.CACHED_CONFIG:
            return cls.CACHED_CONFIG[cls.IDENTIFIER_SYSTEM]
        identifier = PatientIdentifierConfig.objects.filter(
            config__system=cls.IDENTIFIER_SYSTEM,
            facility__isnull=True,
        ).first()
        if not identifier:
            identifier = cls.create_identifier()
        cls.CACHED_CONFIG[cls.IDENTIFIER_SYSTEM] = identifier
        return cls.CACHED_CONFIG[cls.IDENTIFIER_SYSTEM]

    @classmethod
    def create_identifier(cls):
        return PatientIdentifierConfig.objects.create(
            facility=None,
            status=PatientIdentifierStatus.active.value,
            config=IdentifierConfig(
                use=PatientIdentifierUse.secondary,
                system=cls.IDENTIFIER_SYSTEM,
                required=False,
                unique=False,
                regex="",
                display=cls.DISPLAY,
                auto_maintained=True,
                retrieve_config=PatientIdentifierRetrieveConfig(
                    retrieve_with_year_of_birth=cls.RETRIEVE_WITH_YOB,
                    retrieve_with_dob=False,
                    retrieve_with_otp=False,
                    retrieve_partial_search=cls.PARTIAL_SEARCH,
                ),
            ).model_dump(mode="json"),
        )

    @classmethod
    def get_value(cls, patient):
        return None

    @classmethod
    def update_identifier(cls, patient):
        identifier = cls.get__or_create_system_name_identifier_config()
        current_identifier = PatientIdentifier.objects.filter(
            patient=patient, config=identifier
        ).first()
        if not current_identifier:
            current_identifier = PatientIdentifier.objects.create(
                patient=patient, config=identifier, value=cls.get_value(patient)
            )
        else:
            current_identifier.value = cls.get_value(patient)
            current_identifier.save()
