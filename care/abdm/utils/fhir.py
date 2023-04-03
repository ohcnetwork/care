from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.coding import Coding
from fhir.resources.domainresource import DomainResource
from fhir.resources.encounter import Encounter


def get_reference_url(resource: DomainResource):
    return f"{resource.resource_type}/{resource.id}"


def create_encounter(consultation):
    return Encounter(
        **{
            "id": str(consultation.external_id),
            "status": "discharged" if consultation.discharge_date else "in-progress",
            "class": Coding(code="IMP", display="Inpatient Encounter"),
        }
    )


def create_consultation_bundle(consultation):
    encounter = create_encounter(consultation)

    return Bundle(
        id=str(consultation.patient.external_id),
        type="collection",
        entry=[BundleEntry(fullUrl=get_reference_url(encounter), resource=encounter)],
    )
