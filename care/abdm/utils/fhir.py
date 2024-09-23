import base64
from datetime import UTC, datetime
from uuid import uuid4 as uuid

from fhir.resources.address import Address
from fhir.resources.annotation import Annotation
from fhir.resources.attachment import Attachment
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.careplan import CarePlan
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.composition import Composition, CompositionSection
from fhir.resources.condition import Condition
from fhir.resources.contactpoint import ContactPoint
from fhir.resources.diagnosticreport import DiagnosticReport
from fhir.resources.documentreference import DocumentReference, DocumentReferenceContent
from fhir.resources.dosage import Dosage
from fhir.resources.encounter import Encounter, EncounterDiagnosis
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
from fhir.resources.procedure import Procedure
from fhir.resources.quantity import Quantity
from fhir.resources.reference import Reference

from care.facility.models.file_upload import FileUpload
from care.facility.models.icd11_diagnosis import REVERSE_CONDITION_VERIFICATION_STATUSES
from care.facility.models.patient_investigation import InvestigationValue
from care.facility.static_data.icd11 import get_icd11_diagnosis_object_by_id


class Fhir:
    def __init__(self, consultation):
        self.consultation = consultation

        self._patient_profile = None
        self._practitioner_profile = None
        self._organization_profile = None
        self._encounter_profile = None
        self._careplan_profile = None
        self._diagnostic_report_profile = None
        self._immunization_profile = None
        self._medication_profiles = []
        self._medication_request_profiles = []
        self._observation_profiles = []
        self._document_reference_profiles = []
        self._condition_profiles = []
        self._procedure_profiles = []

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
        name = (
            (
                self.consultation.treating_physician
                and f"{self.consultation.treating_physician.first_name} {self.consultation.treating_physician.last_name}"
            )
            or self.consultation.deprecated_verified_by
            or f"{self.consultation.created_by.first_name} {self.consultation.created_by.last_name}"
        )
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

    def _condition(self, diagnosis_id, verification_status):
        diagnosis = get_icd11_diagnosis_object_by_id(diagnosis_id)
        [code, label] = diagnosis.label.split(" ", 1)
        condition_profile = Condition(
            id=diagnosis_id,
            identifier=[Identifier(value=diagnosis_id)],
            category=[
                CodeableConcept(
                    coding=[
                        Coding(
                            system="http://terminology.hl7.org/CodeSystem/condition-category",
                            code="encounter-diagnosis",
                            display="Encounter Diagnosis",
                        )
                    ],
                    text="Encounter Diagnosis",
                )
            ],
            verificationStatus=CodeableConcept(
                coding=[
                    Coding(
                        system="http://terminology.hl7.org/CodeSystem/condition-ver-status",
                        code=verification_status,
                        display=REVERSE_CONDITION_VERIFICATION_STATUSES[
                            verification_status
                        ],
                    )
                ]
            ),
            code=CodeableConcept(
                coding=[
                    Coding(
                        system="http://id.who.int/icd/release/11/mms",
                        code=code,
                        display=label,
                    )
                ],
                text=diagnosis.label,
            ),
            subject=self._reference(self._patient()),
        )

        self._condition_profiles.append(condition_profile)
        return condition_profile

    def _procedure(self, procedure):
        procedure_profile = Procedure(
            id=str(uuid()),
            status="completed",
            code=CodeableConcept(
                text=procedure["procedure"],
            ),
            subject=self._reference(self._patient()),
            performedDateTime=(
                f"{procedure['time']}:00+05:30" if not procedure["repetitive"] else None
            ),
            performedString=(
                f"Every {procedure['frequency']}" if procedure["repetitive"] else None
            ),
        )

        self._procedure_profiles.append(procedure_profile)
        return procedure_profile

    def _careplan(self):
        if self._careplan_profile:
            return self._careplan_profile

        self._careplan_profile = CarePlan(
            id=str(uuid()),
            status="completed",
            intent="plan",
            title="Care Plan",
            description="This includes Treatment Summary, Prescribed Medication, General Notes and Special Instructions",
            period=Period(
                start=self.consultation.encounter_date.isoformat(),
                end=(
                    self.consultation.discharge_date.isoformat()
                    if self.consultation.discharge_date
                    else None
                ),
            ),
            note=[
                Annotation(text=self.consultation.treatment_plan),
                Annotation(text=self.consultation.consultation_notes),
                Annotation(text=self.consultation.special_instruction),
            ],
            subject=self._reference(self._patient()),
        )

        return self._careplan_profile

    def _diagnostic_report(self):
        if self._diagnostic_report_profile:
            return self._diagnostic_report_profile

        self._diagnostic_report_profile = DiagnosticReport(
            id=str(uuid()),
            status="final",
            code=CodeableConcept(text="Investigation/Test Results"),
            result=list(
                map(
                    lambda investigation: self._reference(
                        self._observation(
                            title=investigation.investigation.name,
                            value={
                                "value": investigation.value,
                                "unit": investigation.investigation.unit,
                            },
                            id=str(investigation.external_id),
                            date=investigation.created_date.isoformat(),
                        )
                    ),
                    InvestigationValue.objects.filter(consultation=self.consultation),
                )
            ),
            subject=self._reference(self._patient()),
            performer=[self._reference(self._organization())],
            resultsInterpreter=[self._reference(self._organization())],
            conclusion="Refer to Doctor. To be correlated with further study.",
        )

        return self._diagnostic_report_profile

    def _observation(self, title, value, id, date):
        if not value or (isinstance(value, dict) and not value["value"]):
            return None

        return Observation(
            id=(
                f"{id}.{title.replace(' ', '').replace('_', '-')}"
                if id and title
                else str(uuid())
            ),
            status="final",
            effectiveDateTime=date if date else None,
            code=CodeableConcept(text=title),
            valueQuantity=(
                Quantity(value=str(value["value"]), unit=value["unit"])
                if isinstance(value, dict)
                else None
            ),
            valueString=value if isinstance(value, str) else None,
            component=(
                list(
                    map(
                        lambda component: ObservationComponent(
                            code=CodeableConcept(text=component["title"]),
                            valueQuantity=(
                                Quantity(
                                    value=component["value"], unit=component["unit"]
                                )
                                if isinstance(component, dict)
                                else None
                            ),
                            valueString=(
                                component if isinstance(component, str) else None
                            ),
                        ),
                        value,
                    )
                )
                if isinstance(value, list)
                else None
            ),
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
                {"value": daily_round.ventilator_spo2, "unit": "%"},
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
                (
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
                    else None
                ),
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

    def _encounter(self, include_diagnosis=False):
        if self._encounter_profile is not None:
            return self._encounter_profile

        id = str(self.consultation.external_id)
        status = "finished" if self.consultation.discharge_date else "in-progress"
        period_start = self.consultation.encounter_date.isoformat()
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
                "diagnosis": (
                    list(
                        map(
                            lambda consultation_diagnosis: EncounterDiagnosis(
                                condition=self._reference(
                                    self._condition(
                                        consultation_diagnosis.diagnosis_id,
                                        consultation_diagnosis.verification_status,
                                    ),
                                )
                            ),
                            self.consultation.diagnoses.all(),
                        )
                    )
                    if include_diagnosis
                    else None
                ),
            }
        )

        return self._encounter_profile

    def _immunization(self):
        if self._immunization_profile:
            return self._immunization_profile

        if not self.consultation.patient.is_vaccinated:
            return None

        self._immunization_profile = Immunization(
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

    def _document_reference(self, file):
        id = str(file.external_id)
        content_type, content = file.file_contents()
        document_reference_profile = DocumentReference(
            id=id,
            identifier=[Identifier(value=id)],
            status="current",
            type=CodeableConcept(text=file.internal_name.split(".")[0]),
            content=[
                DocumentReferenceContent(
                    attachment=Attachment(
                        contentType=content_type, data=base64.b64encode(content)
                    )
                )
            ],
            author=[self._reference(self._organization())],
        )

        self._document_reference_profiles.append(document_reference_profile)
        return document_reference_profile

    def _medication(self, name):
        medication_profile = Medication(id=str(uuid()), code=CodeableConcept(text=name))

        self._medication_profiles.append(medication_profile)
        return medication_profile

    def _medication_request(self, medicine):
        id = str(uuid())
        prescription_date = (
            self.consultation.encounter_date.isoformat()
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
            date=datetime.now(UTC).isoformat(),
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

    def _health_document_composition(self):
        id = str(uuid())  # TODO: use identifiable id
        return Composition(
            id=id,
            identifier=Identifier(value=id),
            status="final",  # TODO: use appropriate one
            type=CodeableConcept(
                coding=[
                    Coding(
                        system="https://projecteka.in/sct",
                        code="419891008",
                        display="Record artifact",
                    )
                ]
            ),
            title="Health Document Record",
            date=datetime.now(UTC).isoformat(),
            section=[
                CompositionSection(
                    title="Health Document Record",
                    code=CodeableConcept(
                        coding=[
                            Coding(
                                system="https://projecteka.in/sct",
                                code="419891008",
                                display="Record artifact",
                            )
                        ]
                    ),
                    entry=list(
                        map(
                            lambda file: self._reference(
                                self._document_reference(file)
                            ),
                            FileUpload.objects.filter(
                                associating_id=self.consultation.id
                            ),
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
            date=datetime.now(UTC).isoformat(),
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
            date=datetime.now(UTC).isoformat(),
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
                    entry=[
                        *(
                            [self._reference(self._immunization())]
                            if self._immunization()
                            else []
                        )
                    ],
                    emptyReason=(
                        None
                        if self._immunization()
                        else CodeableConcept(
                            coding=[Coding(code="notasked", display="Not Asked")]
                        )
                    ),
                ),
            ],
            subject=self._reference(self._patient()),
            encounter=self._reference(self._encounter()),
            author=[self._reference(self._organization())],
        )

    def _diagnostic_report_composition(self):
        id = str(uuid())  # TODO: use identifiable id
        return Composition(
            id=id,
            identifier=Identifier(value=id),
            status="final",  # TODO: use appropriate one
            type=CodeableConcept(
                coding=[
                    Coding(
                        system="https://projecteka.in/sct",
                        code="721981007",
                        display="Diagnostic Report",
                    ),
                ],
            ),
            title="Diagnostic Report",
            date=datetime.now(UTC).isoformat(),
            section=[
                CompositionSection(
                    title="Investigation Report",
                    code=CodeableConcept(
                        coding=[
                            Coding(
                                system="https://projecteka.in/sct",
                                code="721981007",
                                display="Diagnostic Report",
                            ),
                        ],
                    ),
                    entry=[self._reference(self._diagnostic_report())],
                ),
            ],
            subject=self._reference(self._patient()),
            encounter=self._reference(self._encounter()),
            author=[self._reference(self._organization())],
        )

    def _discharge_summary_composition(self):
        id = str(uuid())  # TODO: use identifiable id
        return Composition(
            id=id,
            identifier=Identifier(value=id),
            status="final",  # TODO: use appropriate one
            type=CodeableConcept(
                coding=[
                    Coding(
                        system="https://projecteka.in/sct",
                        code="373942005",
                        display="Discharge Summary Record",
                    )
                ]
            ),
            title="Discharge Summary Document",
            date=datetime.now(UTC).isoformat(),
            section=[
                CompositionSection(
                    title="Prescribed medications",
                    code=CodeableConcept(
                        coding=[
                            Coding(
                                system="https://projecteka.in/sct",
                                code="440545006",
                                display="Prescription",
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
                ),
                CompositionSection(
                    title="Health Documents",
                    code=CodeableConcept(
                        coding=[
                            Coding(
                                system="https://projecteka.in/sct",
                                code="419891008",
                                display="Record",
                            )
                        ]
                    ),
                    entry=list(
                        map(
                            lambda file: self._reference(
                                self._document_reference(file)
                            ),
                            FileUpload.objects.filter(
                                associating_id=self.consultation.id
                            ),
                        )
                    ),
                ),
                *list(
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
                CompositionSection(
                    title="Procedures",
                    code=CodeableConcept(
                        coding=[
                            Coding(
                                system="https://projecteka.in/sct",
                                code="371525003",
                                display="Clinical procedure report",
                            )
                        ]
                    ),
                    entry=list(
                        map(
                            lambda procedure: self._reference(
                                self._procedure(procedure)
                            ),
                            self.consultation.procedure,
                        )
                    ),
                ),
                CompositionSection(
                    title="Care Plan",
                    code=CodeableConcept(
                        coding=[
                            Coding(
                                system="https://projecteka.in/sct",
                                code="734163000",
                                display="Care Plan",
                            )
                        ]
                    ),
                    entry=[self._reference(self._careplan())],
                ),
            ],
            subject=self._reference(self._patient()),
            encounter=self._reference(self._encounter(include_diagnosis=True)),
            author=[self._reference(self._organization())],
        )

    def _op_consultation_composition(self):
        id = str(uuid())  # TODO: use identifiable id
        return Composition(
            id=id,
            identifier=Identifier(value=id),
            status="final",  # TODO: use appropriate one
            type=CodeableConcept(
                coding=[
                    Coding(
                        system="https://projecteka.in/sct",
                        code="371530004",
                        display="Clinical consultation report",
                    )
                ]
            ),
            title="OP Consultation Document",
            date=datetime.now(UTC).isoformat(),
            section=[
                CompositionSection(
                    title="Prescribed medications",
                    code=CodeableConcept(
                        coding=[
                            Coding(
                                system="https://projecteka.in/sct",
                                code="440545006",
                                display="Prescription",
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
                ),
                CompositionSection(
                    title="Health Documents",
                    code=CodeableConcept(
                        coding=[
                            Coding(
                                system="https://projecteka.in/sct",
                                code="419891008",
                                display="Record",
                            )
                        ]
                    ),
                    entry=list(
                        map(
                            lambda file: self._reference(
                                self._document_reference(file)
                            ),
                            FileUpload.objects.filter(
                                associating_id=self.consultation.id
                            ),
                        )
                    ),
                ),
                *list(
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
                CompositionSection(
                    title="Procedures",
                    code=CodeableConcept(
                        coding=[
                            Coding(
                                system="https://projecteka.in/sct",
                                code="371525003",
                                display="Clinical procedure report",
                            )
                        ]
                    ),
                    entry=list(
                        map(
                            lambda procedure: self._reference(
                                self._procedure(procedure)
                            ),
                            self.consultation.procedure,
                        )
                    ),
                ),
                CompositionSection(
                    title="Care Plan",
                    code=CodeableConcept(
                        coding=[
                            Coding(
                                system="https://projecteka.in/sct",
                                code="734163000",
                                display="Care Plan",
                            )
                        ]
                    ),
                    entry=[self._reference(self._careplan())],
                ),
            ],
            subject=self._reference(self._patient()),
            encounter=self._reference(self._encounter(include_diagnosis=True)),
            author=[self._reference(self._organization())],
        )

    def _bundle_entry(self, resource):
        return BundleEntry(fullUrl=self._reference_url(resource), resource=resource)

    def create_prescription_record(self):
        id = str(uuid())
        now = datetime.now(UTC).isoformat()
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
        now = datetime.now(UTC).isoformat()
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
        now = datetime.now(UTC).isoformat()
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

    def create_diagnostic_report_record(self):
        id = str(uuid())
        now = datetime.now(UTC).isoformat()
        return Bundle(
            id=id,
            identifier=Identifier(value=id),
            type="document",
            meta=Meta(lastUpdated=now),
            timestamp=now,
            entry=[
                self._bundle_entry(self._diagnostic_report_composition()),
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

    def create_health_document_record(self):
        id = str(uuid())
        now = datetime.now(UTC).isoformat()
        return Bundle(
            id=id,
            identifier=Identifier(value=id),
            type="document",
            meta=Meta(lastUpdated=now),
            timestamp=now,
            entry=[
                self._bundle_entry(self._health_document_composition()),
                self._bundle_entry(self._practioner()),
                self._bundle_entry(self._patient()),
                self._bundle_entry(self._organization()),
                self._bundle_entry(self._encounter()),
                *list(
                    map(
                        lambda resource: self._bundle_entry(resource),
                        self._document_reference_profiles,
                    )
                ),
            ],
        ).json()

    def create_discharge_summary_record(self):
        id = str(uuid())
        now = datetime.now(UTC).isoformat()
        return Bundle(
            id=id,
            identifier=Identifier(value=id),
            type="document",
            meta=Meta(lastUpdated=now),
            timestamp=now,
            entry=[
                self._bundle_entry(self._discharge_summary_composition()),
                self._bundle_entry(self._practioner()),
                self._bundle_entry(self._patient()),
                self._bundle_entry(self._organization()),
                self._bundle_entry(self._encounter()),
                self._bundle_entry(self._careplan()),
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
                *list(
                    map(
                        lambda resource: self._bundle_entry(resource),
                        self._condition_profiles,
                    )
                ),
                *list(
                    map(
                        lambda resource: self._bundle_entry(resource),
                        self._procedure_profiles,
                    )
                ),
                *list(
                    map(
                        lambda resource: self._bundle_entry(resource),
                        self._document_reference_profiles,
                    )
                ),
                *list(
                    map(
                        lambda resource: self._bundle_entry(resource),
                        self._observation_profiles,
                    )
                ),
            ],
        ).json()

    def create_op_consultation_record(self):
        id = str(uuid())
        now = datetime.now(UTC).isoformat()
        return Bundle(
            id=id,
            identifier=Identifier(value=id),
            type="document",
            meta=Meta(lastUpdated=now),
            timestamp=now,
            entry=[
                self._bundle_entry(self._op_consultation_composition()),
                self._bundle_entry(self._practioner()),
                self._bundle_entry(self._patient()),
                self._bundle_entry(self._organization()),
                self._bundle_entry(self._encounter()),
                self._bundle_entry(self._careplan()),
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
                *list(
                    map(
                        lambda resource: self._bundle_entry(resource),
                        self._condition_profiles,
                    )
                ),
                *list(
                    map(
                        lambda resource: self._bundle_entry(resource),
                        self._procedure_profiles,
                    )
                ),
                *list(
                    map(
                        lambda resource: self._bundle_entry(resource),
                        self._document_reference_profiles,
                    )
                ),
                *list(
                    map(
                        lambda resource: self._bundle_entry(resource),
                        self._observation_profiles,
                    )
                ),
            ],
        ).json()

    def create_record(self, record_type):
        if record_type == "Prescription":
            return self.create_prescription_record()
        if record_type == "WellnessRecord":
            return self.create_wellness_record()
        if record_type == "ImmunizationRecord":
            return self.create_immunization_record()
        if record_type == "HealthDocumentRecord":
            return self.create_health_document_record()
        if record_type == "DiagnosticReport":
            return self.create_diagnostic_report_record()
        if record_type == "DischargeSummary":
            return self.create_discharge_summary_record()
        if record_type == "OPConsultation":
            return self.create_op_consultation_record()
        return self.create_discharge_summary_record()
