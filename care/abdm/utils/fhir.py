import json

from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.coding import Coding
from fhir.resources.domainresource import DomainResource
from fhir.resources.encounter import Encounter


def get_reference_url(resource: DomainResource):
    return f"{resource.resource_type}/{resource.id}"


def create_encounter(consultation):
    return Encounter(
        **{
            "id": str(str(consultation.external_id)),
            "status": "discharged" if consultation.discharge_date else "in-progress",
            "class": Coding(code="IMP", display="Inpatient Encounter"),
        }
    )


def create_consultation_bundle(consultation):
    encounter = create_encounter(consultation)

    return json.dumps(
        {
            "resourceType": "Bundle",
            "id": "3739707e-1123-46fe-918f-b52d880e4e7f",
            "meta": {"lastUpdated": "2016-08-07T00:00:00.000+05:30"},
            "identifier": {
                "system": "https://www.max.in/bundle",
                "value": "3739707e-1123-46fe-918f-b52d880e4e7f",
            },
            "type": "document",
            "timestamp": "2016-08-07T00:00:00.000+05:30",
            "entry": [
                {
                    "fullUrl": "Composition/c63d1435-b6b6-46c4-8163-33133bf0d9bf",
                    "resource": {
                        "resourceType": "Composition",
                        "id": "c63d1435-b6b6-46c4-8163-33133bf0d9bf",
                        "identifier": {
                            "system": "https://www.max.in/document",
                            "value": "c63d1435-b6b6-46c4-8163-33133bf0d9bf",
                        },
                        "status": "final",
                        "type": {
                            "coding": [
                                {
                                    "system": "https://projecteka.in/sct",
                                    "code": "440545006",
                                    "display": "Prescription record",
                                }
                            ]
                        },
                        "subject": {
                            "reference": "Patient/1019f565-065a-4287-93fd-a3db4cda7fe4"
                        },
                        "encounter": {
                            "reference": f"Encounter/{str(consultation.external_id)}"
                        },
                        "date": "2016-08-07T00:00:00.605+05:30",
                        "author": [
                            {
                                "reference": "Practitioner/MAX5001",
                                "display": "Dr Laxmikanth J",
                            }
                        ],
                        "title": "Prescription",
                        "section": [
                            {
                                "title": "OPD Prescription",
                                "code": {
                                    "coding": [
                                        {
                                            "system": "https://projecteka.in/sct",
                                            "code": "440545006",
                                            "display": "Prescription record",
                                        }
                                    ]
                                },
                                "entry": [
                                    {
                                        "reference": "MedicationRequest/68d9667c-00c3-455f-b75d-d580950498a0"
                                    }
                                ],
                            }
                        ],
                    },
                },
                {
                    "fullUrl": "Practitioner/MAX5001",
                    "resource": {
                        "resourceType": "Practitioner",
                        "id": "MAX5001",
                        "identifier": [
                            {
                                "system": "https://www.mciindia.in/doctor",
                                "value": "MAX5001",
                            }
                        ],
                        "name": [
                            {"text": "Laxmikanth J", "prefix": ["Dr"], "suffix": ["MD"]}
                        ],
                    },
                },
                {
                    "fullUrl": "Patient/1019f565-065a-4287-93fd-a3db4cda7fe4",
                    "resource": {
                        "resourceType": "Patient",
                        "id": "1019f565-065a-4287-93fd-a3db4cda7fe4",
                        "name": [{"text": "KhavinShankar G"}],
                        "gender": "male",
                    },
                },
                {
                    "fullUrl": f"Encounter/{str(consultation.external_id)}",
                    "resource": {
                        "resourceType": "Encounter",
                        "id": str(consultation.external_id),
                        "status": "finished",
                        "class": {
                            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                            "code": "AMB",
                            "display": "Outpatient visit",
                        },
                        "subject": {
                            "reference": "Patient/1019f565-065a-4287-93fd-a3db4cda7fe4"
                        },
                        "period": {"start": "2016-08-07T00:00:00+05:30"},
                    },
                },
                {
                    "fullUrl": "Medication/54ab5657-5e79-4461-a823-20e522eb337d",
                    "resource": {
                        "resourceType": "Medication",
                        "id": "54ab5657-5e79-4461-a823-20e522eb337d",
                        "code": {
                            "coding": [
                                {
                                    "system": "https://projecteka.in/act",
                                    "code": "R05CB02",
                                    "display": "bromhexine 24 mg",
                                }
                            ]
                        },
                    },
                },
                {
                    "fullUrl": "MedicationRequest/68d9667c-00c3-455f-b75d-d580950498a0",
                    "resource": {
                        "resourceType": "MedicationRequest",
                        "id": "68d9667c-00c3-455f-b75d-d580950498a0",
                        "status": "active",
                        "intent": "order",
                        "medicationReference": {
                            "reference": "Medication/54ab5657-5e79-4461-a823-20e522eb337d"
                        },
                        "subject": {
                            "reference": "Patient/1019f565-065a-4287-93fd-a3db4cda7fe4"
                        },
                        "authoredOn": "2016-08-07T00:00:00+05:30",
                        "requester": {"reference": "Practitioner/MAX5001"},
                        "dosageInstruction": [{"text": "1 capsule 2 times a day"}],
                    },
                },
            ],
        }
    )

    return Bundle(
        id=str(consultation.patient.external_id),
        type="document",
        entry=[BundleEntry(fullUrl=get_reference_url(encounter), resource=encounter)],
    ).json()
