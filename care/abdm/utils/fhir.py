from datetime import datetime, timezone
from uuid import uuid4 as uuid

from fhir.resources.address import Address
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.composition import Composition, CompositionSection
from fhir.resources.contactpoint import ContactPoint
from fhir.resources.dosage import Dosage
from fhir.resources.encounter import Encounter
from fhir.resources.humanname import HumanName
from fhir.resources.identifier import Identifier
from fhir.resources.immunization import Immunization, ImmunizationProtocolApplied
from fhir.resources.medication import Medication
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.meta import Meta
from fhir.resources.observation import Observation, ObservationComponent
from fhir.resources.organization import Organization
from fhir.resources.patient import Patient
from fhir.resources.period import Period
from fhir.resources.practitioner import Practitioner
from fhir.resources.quantity import Quantity
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
        self._observation_profiles = []

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
        hip_id = "IN3210000017"  # TODO: make it dynamic
        name = self.consultation.facility.name
        phone = self.consultation.facility.phone_number
        address = self.consultation.facility.address
        local_body = self.consultation.facility.local_body.name
        district = self.consultation.facility.district.name
        state = self.consultation.facility.state.name
        pincode = self.consultation.facility.pincode
        self._organization_profile = Organization(
            id=id,
            identifier=[
                Identifier(system="https://facilitysbx.ndhm.gov.in", value=hip_id)
            ],
            name=name,
            telecom=[ContactPoint(system="phone", value=phone)],
            address=[
                Address(
                    line=[address, local_body],
                    district=district,
                    state=state,
                    postalCode=pincode,
                    country="INDIA",
                )
            ],
        )

        return self._organization_profile

    def _observation(self, title, value, id, date):
        if not value or (type(value) == dict and not value["value"]):
            return

        return Observation(
            id=f"{id}.{title.replace(' ', '')}" if id and title else str(uuid()),
            status="final",
            effectiveDateTime=date if date else None,
            code=CodeableConcept(text=title),
            valueQuantity=Quantity(value=str(value["value"]), unit=value["unit"])
            if type(value) == dict
            else None,
            valueString=value if type(value) == str else None,
            component=list(
                map(
                    lambda component: ObservationComponent(
                        code=CodeableConcept(text=component["title"]),
                        valueQuantity=Quantity(
                            value=component["value"], unit=component["unit"]
                        )
                        if type(component) == dict
                        else None,
                        valueString=component if type(component) == str else None,
                    ),
                    value,
                )
            )
            if type(value) == list
            else None,
        )

    def _observations_from_daily_round(self, daily_round):
        id = str(daily_round.external_id)
        date = daily_round.created_date.isoformat()
        observation_profiles = [
            self._observation(
                "Temperature",
                {"value": daily_round.temperature, "unit": "F"},
                id,
                date,
            ),
            self._observation(
                "SpO2",
                {"value": daily_round.spo2, "unit": "%"},
                id,
                date,
            ),
            self._observation(
                "Pulse",
                {"value": daily_round.pulse, "unit": "bpm"},
                id,
                date,
            ),
            self._observation(
                "Resp",
                {"value": daily_round.resp, "unit": "bpm"},
                id,
                date,
            ),
            self._observation(
                "Blood Pressure",
                [
                    {
                        "title": "Systolic Blood Pressure",
                        "value": daily_round.bp["systolic"],
                        "unit": "mmHg",
                    },
                    {
                        "title": "Diastolic Blood Pressure",
                        "value": daily_round.bp["diastolic"],
                        "unit": "mmHg",
                    },
                ]
                if "systolic" in daily_round.bp and "diastolic" in daily_round.bp
                else None,
                id,
                date,
            ),
        ]

        # TODO: do it for other fields like bp, pulse, spo2, ...

        observation_profiles = list(
            filter(lambda profile: profile is not None, observation_profiles)
        )
        self._observation_profiles.extend(observation_profiles)
        return observation_profiles

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

    def _immunization(self):
        if not self.consultation.patient.is_vaccinated:
            return

        return Immunization(
            id=str(uuid()),
            status="completed",
            identifier=[
                Identifier(
                    type=CodeableConcept(text="Covin Id"),
                    value=self.consultation.patient.covin_id,
                )
            ],
            vaccineCode=CodeableConcept(
                coding=[
                    Coding(
                        system="http://snomed.info/sct",
                        code="1119305005",
                        display="COVID-19 antigen vaccine",
                    )
                ],
                text=self.consultation.patient.vaccine_name,
            ),
            patient=self._reference(self._patient()),
            route=CodeableConcept(
                coding=[
                    Coding(
                        system="https://projecteka.in/sct",
                        code="47625008",
                        display="Intravenous route",
                    )
                ]
            ),
            occurrenceDateTime=self.consultation.patient.last_vaccinated_date.isoformat(),
            protocolApplied=[
                ImmunizationProtocolApplied(
                    doseNumberPositiveInt=self.consultation.patient.number_of_doses
                )
            ],
        )

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
        dosage_text = f"{medicine['dosage_new']} / {medicine['dosage']} for {medicine['days']} days"

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

    def _prescription_composition(self):
        id = str(uuid())  # TODO: use identifiable id
        return Composition(
            id=id,
            identifier=Identifier(value=id),
            status="final",  # TODO: use appropriate one
            type=CodeableConcept(
                coding=[
                    Coding(
                        system="https://projecteka.in/sct",
                        code="440545006",
                        display="Prescription record",
                    )
                ]
            ),
            title="Prescription",
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

    def _wellness_composition(self):
        id = str(uuid())  # TODO: use identifiable id
        return Composition(
            id=id,
            identifier=Identifier(value=id),
            status="final",  # TODO: use appropriate one
            type=CodeableConcept(
                coding=[
                    Coding(
                        system="https://projecteka.in/sct",
                        display="Wellness Record",
                    )
                ]
            ),
            title="Wellness Record",
            date=datetime.now(timezone.utc).isoformat(),
            section=list(
                map(
                    lambda daily_round: CompositionSection(
                        title=f"Daily Round - {daily_round.created_date}",
                        code=CodeableConcept(
                            coding=[
                                Coding(
                                    system="https://projecteka.in/sct",
                                    display="Wellness Record",
                                )
                            ]
                        ),
                        entry=list(
                            map(
                                lambda observation_profile: self._reference(
                                    observation_profile
                                ),
                                self._observations_from_daily_round(daily_round),
                            )
                        ),
                    ),
                    self.consultation.daily_rounds.all(),
                )
            ),
            subject=self._reference(self._patient()),
            encounter=self._reference(self._encounter()),
            author=[self._reference(self._organization())],
        )

    def _immunization_composition(self):
        id = str(uuid())  # TODO: use identifiable id
        return Composition(
            id=id,
            identifier=Identifier(value=id),
            status="final",  # TODO: use appropriate one
            type=CodeableConcept(
                coding=[
                    Coding(
                        system="https://projecteka.in/sct",
                        code="41000179103",
                        display="Immunization Record",
                    ),
                ],
            ),
            title="Immunization",
            date=datetime.now(timezone.utc).isoformat(),
            section=[
                CompositionSection(
                    title="IPD Immunization",
                    code=CodeableConcept(
                        coding=[
                            Coding(
                                system="https://projecteka.in/sct",
                                code="41000179103",
                                display="Immunization Record",
                            ),
                        ],
                    ),
                    entry=[self._reference(self._immunization())],
                ),
            ],
            subject=self._reference(self._patient()),
            encounter=self._reference(self._encounter()),
            author=[self._reference(self._organization())],
        )

    def _bundle_entry(self, resource):
        return BundleEntry(fullUrl=self._reference_url(resource), resource=resource)

    def create_prescription_record(self):
        id = str(uuid())
        now = datetime.now(timezone.utc).isoformat()
        return Bundle(
            id=id,
            identifier=Identifier(value=id),
            type="document",
            meta=Meta(lastUpdated=now),
            timestamp=now,
            entry=[
                self._bundle_entry(self._prescription_composition()),
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

    def create_wellness_record(self):
        id = str(uuid())
        now = datetime.now(timezone.utc).isoformat()
        return Bundle(
            id=id,
            identifier=Identifier(value=id),
            type="document",
            meta=Meta(lastUpdated=now),
            timestamp=now,
            entry=[
                self._bundle_entry(self._wellness_composition()),
                self._bundle_entry(self._practioner()),
                self._bundle_entry(self._patient()),
                self._bundle_entry(self._organization()),
                self._bundle_entry(self._encounter()),
                *list(
                    map(
                        lambda resource: self._bundle_entry(resource),
                        self._observation_profiles,
                    )
                ),
            ],
        ).json()

    def create_immunization_record(self):
        id = str(uuid())
        now = datetime.now(timezone.utc).isoformat()
        return Bundle(
            id=id,
            identifier=Identifier(value=id),
            type="document",
            meta=Meta(lastUpdated=now),
            timestamp=now,
            entry=[
                self._bundle_entry(self._immunization_composition()),
                self._bundle_entry(self._practioner()),
                self._bundle_entry(self._patient()),
                self._bundle_entry(self._organization()),
                self._bundle_entry(self._encounter()),
                self._bundle_entry(self._immunization()),
            ],
        ).json()
