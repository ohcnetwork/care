import json
from datetime import datetime, timezone
from uuid import uuid4 as uuid

from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.composition import Composition, CompositionSection
from fhir.resources.dosage import Dosage
from fhir.resources.encounter import Encounter
from fhir.resources.humanname import HumanName
from fhir.resources.identifier import Identifier
from fhir.resources.medication import Medication
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.meta import Meta
from fhir.resources.organization import Organization
from fhir.resources.patient import Patient
from fhir.resources.period import Period
from fhir.resources.practitioner import Practitioner
from fhir.resources.reference import Reference


class Fhir:
    def __init__(self, consultation):
        self.consultation = consultation

        self._patient_profile = None
        self._practitioner_profile = None
        self._organization_profile = None
        self._encounter_profile = None
        self._medication_profiles = []
        self._medication_request_profiles = []

    def _reference_url(self, resource=None):
        if resource is None:
            return ""

        return f"{resource.resource_type}/{resource.id}"

    def _reference(self, resource=None):
        if resource is None:
            return None

        return Reference(reference=self._reference_url(resource))

    def _patient(self):
        if self._patient_profile is not None:
            return self._patient_profile

        id = str(self.consultation.patient.external_id)
        name = self.consultation.patient.name
        gender = self.consultation.patient.gender
        self._patient_profile = Patient(
            id=id,
            identifier=[Identifier(value=id)],
            name=[HumanName(text=name)],
            gender="male" if gender == 1 else "female" if gender == 2 else "other",
        )

        return self._patient_profile

    def _practioner(self):
        if self._practitioner_profile is not None:
            return self._practitioner_profile

        id = str(uuid())
        name = self.consultation.verified_by
        self._practitioner_profile = Practitioner(
            id=id,
            identifier=[Identifier(value=id)],
            name=[HumanName(text=name)],
        )

        return self._practitioner_profile

    def _organization(self):
        if self._organization_profile is not None:
            return self._organization_profile

        id = str(self.consultation.facility.external_id)
        name = self.consultation.facility.name
        self._organization_profile = Organization(
            id=id,
            identifier=[Identifier(value=id)],
            name=name,
        )

        return self._organization_profile

    def _encounter(self):
        if self._encounter_profile is not None:
            return self._encounter_profile

        id = str(self.consultation.external_id)
        status = "finished" if self.consultation.discharge_date else "in-progress"
        period_start = self.consultation.admission_date.isoformat()
        period_end = (
            self.consultation.discharge_date.isoformat()
            if self.consultation.discharge_date
            else None
        )
        self._encounter_profile = Encounter(
            **{
                "id": id,
                "identifier": [Identifier(value=id)],
                "status": status,
                "class": Coding(code="IMP", display="Inpatient Encounter"),
                "subject": self._reference(self._patient()),
                "period": Period(start=period_start, end=period_end),
            }
        )

        return self._encounter_profile

    def _medication(self, name):
        medication_profile = Medication(id=str(uuid()), code=CodeableConcept(text=name))

        self._medication_profiles.append(medication_profile)
        return medication_profile

    def _medication_request(self, medicine):
        id = str(uuid())
        prescription_date = (
            self.consultation.admission_date.isoformat()
        )  # TODO: change to the time of prescription
        status = "unknown"  # TODO: get correct status active | on-hold | cancelled | completed | entered-in-error | stopped | draft | unknown
        dosage_text = (
            f"{medicine['dosage_new']} / {medicine['dosage']} for {medicine['days']}"
        )

        medication_profile = self._medication(medicine["medicine"])
        medication_request_profile = MedicationRequest(
            id=id,
            identifier=[Identifier(value=id)],
            status=status,
            intent="order",
            authoredOn=prescription_date,
            dosageInstruction=[Dosage(text=dosage_text)],
            medicationReference=self._reference(medication_profile),
            subject=self._reference(self._patient()),
            requester=self._reference(self._practioner()),
        )

        self._medication_request_profiles.append(medication_request_profile)
        return medication_profile, medication_request_profile

    def _composition(self, type):
        id = str(uuid())  # TODO: use identifiable id
        return Composition(
            id=id,
            identifier=Identifier(value=id),
            status="preliminary" or "final" or "amended",  # TODO: use appropriate one
            type=CodeableConcept(
                coding=[
                    Coding(
                        system="https://projecteka.in/sct",
                        code="440545006",
                        display="Prescription record",
                    )
                ]
            ),  # TODO: make it dynamic
            title=type,  # "Prescription"
            date=datetime.now(timezone.utc).isoformat(),
            section=[
                CompositionSection(
                    title="In Patient Prescriptions",
                    code=CodeableConcept(
                        coding=[
                            Coding(
                                system="https://projecteka.in/sct",
                                code="440545006",
                                display="Prescription record",
                            )
                        ]
                    ),
                    entry=list(
                        map(
                            lambda medicine: self._reference(
                                self._medication_request(medicine)[1]
                            ),
                            self.consultation.discharge_advice,
                        )
                    ),
                )
            ],
            subject=self._reference(self._patient()),
            encounter=self._reference(self._encounter()),
            author=[self._reference(self._organization())],
        )

    pr = {
        "entry": [
            {"fullUrl": "Practitioner/MAX5001", "resource": ""},
            {
                "fullUrl": "Patient/RVH9999",
                "resource": "",
            },
            {
                "fullUrl": "Encounter/dab7fd2b-6a05-4adb-af35-bcffd6c85b81",
                "resource": "",
            },
            {
                "fullUrl": "Medication/54ab5657-5e79-4461-a823-20e522eb337d",
                "resource": "",
            },
            {
                "fullUrl": "MedicationRequest/68d9667c-00c3-455f-b75d-d580950498a0",
                "resource": "",
            },
        ],
    }

    def _bundle_entry(self, resource):
        return BundleEntry(fullUrl=self._reference_url(resource), resource=resource)

    def create_prescription_record(self):
        id = str(uuid())
        now = datetime.now(timezone.utc).isoformat()
        composition_profile = self._composition("Prescription")
        return Bundle(
            id=id,
            identifier=Identifier(value=id),
            type="document",
            meta=Meta(lastUpdated=now),
            timestamp=now,
            entry=[
                self._bundle_entry(composition_profile),
                self._bundle_entry(self._practioner()),
                self._bundle_entry(self._patient()),
                self._bundle_entry(self._organization()),
                self._bundle_entry(self._encounter()),
                *list(
                    map(
                        lambda resource: self._bundle_entry(resource),
                        self._medication_profiles,
                    )
                ),
                *list(
                    map(
                        lambda resource: self._bundle_entry(resource),
                        self._medication_request_profiles,
                    )
                ),
            ],
        ).json()


def create_consultation_bundle(consultation):
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
