from datetime import datetime, timezone
from functools import reduce
from typing import List, Literal, TypedDict

import requests
from fhir.resources import (
    annotation,
    attachment,
    bundle,
    claim,
    claimresponse,
    codeableconcept,
    coding,
    communication,
    communicationrequest,
    condition,
    coverage,
    coverageeligibilityrequest,
    coverageeligibilityresponse,
    domainresource,
    identifier,
    meta,
    organization,
    patient,
    period,
    practitionerrole,
    procedure,
    reference,
)

from config.settings.base import CURRENT_DOMAIN


class PROFILE:
    patient = "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Patient"
    organization = "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Organization"
    coverage = "https://ig.hcxprotocol.io/v0.7.1/StructureDefinition-Coverage.html"
    coverage_eligibility_request = "https://ig.hcxprotocol.io/v0.7.1/StructureDefinition-CoverageEligibilityRequest.html"
    claim = "https://ig.hcxprotocol.io/v0.7.1/StructureDefinition-Claim.html"
    claim_bundle = (
        "https://ig.hcxprotocol.io/v0.7.1/StructureDefinition-ClaimRequestBundle.html"
    )
    coverage_eligibility_request_bundle = "https://ig.hcxprotocol.io/v0.7.1/StructureDefinition-CoverageEligibilityRequestBundle.html"
    practitioner_role = (
        "https://nrces.in/ndhm/fhir/r4/StructureDefinition/PractitionerRole"
    )
    procedure = "http://hl7.org/fhir/R4/procedure.html"
    condition = "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Condition"
    communication = (
        "https://ig.hcxprotocol.io/v0.7.1/StructureDefinition-Communication.html"
    )
    communication_bundle = (
        "https://ig.hcxprotocol.io/v0.7.1/StructureDefinition-CommunicationBundle.html"
    )


class SYSTEM:
    codes = "http://terminology.hl7.org/CodeSystem/v2-0203"
    patient_identifier = "http://gicofIndia.com/beneficiaries"
    provider_identifier = "http://abdm.gov.in/facilities"
    insurer_identifier = "http://irdai.gov.in/insurers"
    coverage_identifier = "https://www.gicofIndia.in/policies"
    coverage_relationship = (
        "http://terminology.hl7.org/CodeSystem/subscriber-relationship"
    )
    priority = "http://terminology.hl7.org/CodeSystem/processpriority"
    claim_identifier = CURRENT_DOMAIN
    claim_type = "http://terminology.hl7.org/CodeSystem/claim-type"
    claim_payee_type = "http://terminology.hl7.org/CodeSystem/payeetype"
    claim_item = "https://pmjay.gov.in/hbp-package-code"
    claim_bundle_identifier = "https://www.tmh.in/bundle"
    coverage_eligibility_request_bundle_identifier = "https://www.tmh.in/bundle"
    practitioner_speciality = "http://snomed.info/sct"
    claim_supporting_info_category = (
        "http://hcxprotocol.io/codes/claim-supporting-info-categories"
    )
    related_claim_relationship = (
        "http://terminology.hl7.org/CodeSystem/ex-relatedclaimrelationship"
    )
    procedure_status = "http://hl7.org/fhir/event-status"
    condition = "http://snomed.info/sct"
    diagnosis_type = "http://terminology.hl7.org/CodeSystem/ex-diagnosistype"
    claim_item_category = "https://irdai.gov.in/benefit-billing-group-code"
    claim_item_category_pmjy = "https://pmjay.gov.in/benefit-billing-group-code"
    communication_identifier = "http://www.providerco.com/communication"
    communication_bundle_identifier = "https://www.tmh.in/bundle"


PRACTIONER_SPECIALITY = {
    "223366009": "Healthcare professional",
    "1421009": "Specialized surgeon",
    "3430008": "Radiation therapist",
    "3842006": "Chiropractor",
    "4162009": "Dental assistant",
    "5275007": "Auxiliary nurse",
    "6816002": "Specialized nurse",
    "6868009": "Hospital administrator",
    "8724009": "Plastic surgeon",
    "11661002": "Neuropathologist",
    "11911009": "Nephrologist",
    "11935004": "Obstetrician",
    "13580004": "School dental assistant",
    "14698002": "Medical microbiologist",
    "17561000": "Cardiologist",
    "18803008": "Dermatologist",
    "18850004": "Laboratory hematologist",
    "19244007": "Gerodontist",
    "20145008": "Removable prosthodontist",
    "21365001": "Specialized dentist",
    "21450003": "Neuropsychiatrist",
    "22515006": "Medical assistant",
    "22731001": "Orthopedic surgeon",
    "22983004": "Thoracic surgeon",
    "23278007": "Community health physician",
    "24430003": "Physical medicine specialist",
    "24590004": "Urologist",
    "25961008": "Electroencephalography specialist",
    "26042002": "Dental hygienist",
    "26369006": "Public health nurse",
    "28229004": "Optometrist",
    "28411006": "Neonatologist",
    "28544002": "Medical biochemist",
    "36682004": "Physiotherapist",
    "37154003": "Periodontist",
    "37504001": "Orthodontist",
    "39677007": "Internal medicine specialist",
    "40127002": "Dietitian (general)",
    "40204001": "Hematologist",
    "40570005": "Interpreter",
    "41672002": "Respiratory disease specialist",
    "41904004": "Medical X-ray technician",
    "43702002": "Occupational health nurse",
    "44652006": "Pharmaceutical assistant",
    "45419001": "Masseur",
    "45440000": "Rheumatologist",
    "45544007": "Neurosurgeon",
    "45956004": "Sanitarian",
    "46255001": "Pharmacist",
    "48740002": "Philologist",
    "49203003": "Dispensing optician",
    "49993003": "Oral surgeon",
    "50149000": "Endodontist",
    "54503009": "Faith healer",
    "56397003": "Neurologist",
    "56466003": "Public health physician",
    "56542007": "Medical record administrator",
    "56545009": "Cardiovascular surgeon",
    "57654006": "Fixed prosthodontist",
    "59058001": "General physician",
    "59169001": "Orthopedic technician",
    "59317003": "Dental prosthesis maker and repairer",
    "59944000": "Psychologist",
    "60008001": "Public health nutritionist",
    "61207006": "Medical pathologist",
    "61246008": "Laboratory medicine specialist",
    "61345009": "Otorhinolaryngologist",
    "61894003": "Endocrinologist",
    "62247001": "Family medicine specialist",
    "63098009": "Clinical immunologist",
    "66476003": "Oral pathologist",
    "66862007": "Radiologist",
    "68867008": "Public health dentist",
    "68950000": "Prosthodontist",
    "69280009": "Specialized physician",
    "71838004": "Gastroenterologist",
    "73265009": "Nursing aid",
    "75271001": "Professional midwife",
    "76166008": "Practical aid (pharmacy)",
    "76231001": "Osteopath",
    "76899008": "Infectious disease specialist",
    "78703002": "General surgeon",
    "78729002": "Diagnostic radiologist",
    "79898004": "Auxiliary midwife",
    "80409005": "Translator",
    "80546007": "Occupational therapist",
    "80584001": "Psychiatrist",
    "80933006": "Nuclear medicine specialist",
    "81464008": "Clinical pathologist",
    "82296001": "Pediatrician",
    "83273008": "Anatomic pathologist",
    "83685006": "Gynecologist",
    "85733003": "General pathologist",
    "88189002": "Anesthesiologist",
    "90201008": "Pedodontist",
    "90655003": "Geriatrics specialist",
    "106289002": "Dentist",
    "106291005": "Dietician AND/OR public health nutritionist",
    "106292003": "Professional nurse",
    "106293008": "Nursing personnel",
    "106294002": "Midwifery personnel",
    "307988006": "Medical technician",
    "159036002": "ECG technician",
    "159037006": "EEG technician",
    "159039009": "AT - Audiology technician",
    "159041005": "Trainee medical technician",
    "721942007": "Cardiovascular perfusionist (occupation)",
    "878786001": "Operating room technician (occupation)",
    "878787005": "Anesthesia technician",
}


class IClaimItem(TypedDict):
    id: str
    name: str
    price: float


class IClaimProcedure(TypedDict):
    id: str
    name: str
    performed: str
    status: Literal[
        "preparation",
        "in-progress",
        "not-done",
        "on-hold",
        "stopped",
        "completed",
        "entered-in-error",
        "unknown",
    ]


class IClaimDiagnosis(TypedDict):
    id: str
    label: str
    code: str
    type: Literal[
        "admitting",
        "clinical",
        "differential",
        "discharge",
        "laboratory",
        "nursing",
        "prenatal",
        "principal",
        "radiology",
        "remote",
        "retrospective",
        "self",
    ]


class IClaimSupportingInfo(TypedDict):
    type: str
    url: str
    name: str


class IRelatedClaim(TypedDict):
    id: str
    type: Literal["prior", "associated"]


FHIR_VALIDATION_URL = "https://staging-hcx.swasth.app/hapi-fhir/fhir/Bundle/$validate"


class Fhir:
    def get_reference_url(self, resource: domainresource.DomainResource):
        return f"{resource.resource_type}/{resource.id}"

    def create_patient_profile(
        self, id: str, name: str, gender: str, phone: str, identifier_value: str
    ):
        return patient.Patient(
            id=id,
            meta=meta.Meta(profile=[PROFILE.patient]),
            identifier=[
                identifier.Identifier(
                    type=codeableconcept.CodeableConcept(
                        coding=[
                            coding.Coding(
                                system=SYSTEM.codes,
                                code="SN",
                                display="Subscriber Number",
                            )
                        ]
                    ),
                    system=SYSTEM.patient_identifier,
                    value=identifier_value,
                )
            ],
            name=[{"text": name}],
            gender=gender,
            telecom=[{"system": "phone", "use": "mobile", "value": phone}],
        )

    def create_provider_profile(self, id: str, name: str, identifier_value: str):
        return organization.Organization(
            id=id,
            meta=meta.Meta(profile=[PROFILE.organization]),
            identifier=[
                identifier.Identifier(
                    type=codeableconcept.CodeableConcept(
                        coding=[
                            coding.Coding(
                                system=SYSTEM.codes,
                                code="AC",
                                display=name,
                            )
                        ]
                    ),
                    system=SYSTEM.provider_identifier,
                    value=identifier_value,
                )
            ],
            name=name,
        )

    def create_insurer_profile(self, id: str, name: str, identifier_value: str):
        return organization.Organization(
            id=id,
            meta=meta.Meta(profile=[PROFILE.organization]),
            identifier=[
                identifier.Identifier(
                    type=codeableconcept.CodeableConcept(
                        coding=[
                            coding.Coding(
                                system=SYSTEM.codes,
                                code="AC",
                                display=name,
                            )
                        ]
                    ),
                    system=SYSTEM.insurer_identifier,
                    value=identifier_value,
                )
            ],
            name=name,
        )

    def create_practitioner_role_profile(
        self, id, identifier_value, speciality: str, phone: str
    ):
        return practitionerrole.PractitionerRole(
            id=id,
            meta=meta.Meta(profile=[PROFILE.practitioner_role]),
            identifier=[
                identifier.Identifier(
                    type=codeableconcept.CodeableConcept(
                        coding=[
                            coding.Coding(
                                system=SYSTEM.codes,
                                code="NP",
                                display="Nurse practitioner number",
                            )
                        ]
                    ),
                    value=identifier_value,
                )
            ],
            specialty=[
                codeableconcept.CodeableConcept(
                    coding=[
                        coding.Coding(
                            system=SYSTEM.practitioner_speciality,
                            code=speciality,
                            display=PRACTIONER_SPECIALITY[speciality],
                        )
                    ]
                )
            ],
            telecom=[{"system": "phone", "value": phone}],
        )

    def create_coverage_profile(
        self,
        id: str,
        identifier_value: str,
        subscriber_id: str,
        patient: patient.Patient,
        insurer: organization.Organization,
        status="active",
        relationship="self",
    ):
        return coverage.Coverage(
            id=id,
            meta=meta.Meta(profile=[PROFILE.coverage]),
            identifier=[
                identifier.Identifier(
                    system=SYSTEM.coverage_identifier, value=identifier_value
                )
            ],
            status=status,
            subscriber=reference.Reference(reference=self.get_reference_url(patient)),
            subscriberId=subscriber_id,
            beneficiary=reference.Reference(reference=self.get_reference_url(patient)),
            relationship=codeableconcept.CodeableConcept(
                coding=[
                    coding.Coding(
                        system=SYSTEM.coverage_relationship,
                        code=relationship,
                    )
                ]
            ),
            payor=[reference.Reference(reference=self.get_reference_url(insurer))],
        )

    def create_coverage_eligibility_request_profile(
        self,
        id: str,
        identifier_value: str,
        patient: patient.Patient,
        enterer: practitionerrole.PractitionerRole,
        provider: organization.Organization,
        insurer: organization.Organization,
        coverage: coverage.Coverage,
        priority="normal",
        status="active",
        purpose="validation",
        service_period_start=datetime.now().astimezone(tz=timezone.utc),
        service_period_end=datetime.now().astimezone(tz=timezone.utc),
    ):
        return coverageeligibilityrequest.CoverageEligibilityRequest(
            id=id,
            meta=meta.Meta(profile=[PROFILE.coverage_eligibility_request]),
            identifier=[identifier.Identifier(value=identifier_value)],
            status=status,
            priority=codeableconcept.CodeableConcept(
                coding=[
                    coding.Coding(
                        system=SYSTEM.priority,
                        code=priority,
                    )
                ]
            ),
            purpose=[purpose],
            patient=reference.Reference(reference=self.get_reference_url(patient)),
            servicedPeriod=period.Period(
                start=service_period_start,
                end=service_period_end,
            ),
            created=datetime.now().astimezone(tz=timezone.utc),
            enterer=reference.Reference(reference=self.get_reference_url(enterer)),
            provider=reference.Reference(reference=self.get_reference_url(provider)),
            insurer=reference.Reference(reference=self.get_reference_url(insurer)),
            insurance=[
                coverageeligibilityrequest.CoverageEligibilityRequestInsurance(
                    coverage=reference.Reference(
                        reference=self.get_reference_url(coverage)
                    )
                )
            ],
        )

    def create_claim_profile(
        self,
        id: str,
        identifier_value: str,
        items: List[IClaimItem],
        patient: patient.Patient,
        provider: organization.Organization,
        insurer: organization.Organization,
        coverage: coverage.Coverage,
        use="claim",
        status="active",
        type="institutional",
        priority="normal",
        claim_payee_type="provider",
        supporting_info=[],
        related_claims=[],
        procedures=[],
        diagnoses=[],
    ):
        return claim.Claim(
            id=id,
            meta=meta.Meta(
                profile=[PROFILE.claim],
            ),
            identifier=[
                identifier.Identifier(
                    system=SYSTEM.claim_identifier, value=identifier_value
                )
            ],
            status=status,
            type=codeableconcept.CodeableConcept(
                coding=[
                    coding.Coding(
                        system=SYSTEM.claim_type,
                        code=type,
                    )
                ]
            ),
            use=use,
            related=list(
                map(
                    lambda related_claim: (
                        claim.ClaimRelated(
                            id=related_claim["id"],
                            relationship=codeableconcept.CodeableConcept(
                                coding=[
                                    coding.Coding(
                                        system=SYSTEM.related_claim_relationship,
                                        code=related_claim["type"],
                                    )
                                ]
                            ),
                            claim=reference.Reference(
                                reference=f'Claim/{related_claim["id"]}'
                            ),
                        )
                    ),
                    related_claims,
                )
            ),
            patient=reference.Reference(reference=self.get_reference_url(patient)),
            created=datetime.now().astimezone(tz=timezone.utc),
            insurer=reference.Reference(reference=self.get_reference_url(insurer)),
            provider=reference.Reference(reference=self.get_reference_url(provider)),
            priority=codeableconcept.CodeableConcept(
                coding=[
                    coding.Coding(
                        system=SYSTEM.priority,
                        code=priority,
                    )
                ]
            ),
            payee=claim.ClaimPayee(
                type=codeableconcept.CodeableConcept(
                    coding=[
                        coding.Coding(
                            system=SYSTEM.claim_payee_type,
                            code=claim_payee_type,
                        )
                    ]
                ),
                party=reference.Reference(reference=self.get_reference_url(provider)),
            ),
            careTeam=[
                claim.ClaimCareTeam(
                    sequence=1,
                    provider=reference.Reference(
                        reference=self.get_reference_url(provider)
                    ),
                )
            ],
            insurance=[
                claim.ClaimInsurance(
                    sequence=1,
                    focal=True,
                    coverage=reference.Reference(
                        reference=self.get_reference_url(coverage)
                    ),
                )
            ],
            item=list(
                map(
                    lambda item, i: (
                        claim.ClaimItem(
                            sequence=i,
                            productOrService=codeableconcept.CodeableConcept(
                                coding=[
                                    coding.Coding(
                                        system=SYSTEM.claim_item,
                                        code=item["id"],
                                        display=item["name"],
                                    )
                                ]
                            ),
                            unitPrice={"value": item["price"], "currency": "INR"},
                            category=codeableconcept.CodeableConcept(
                                coding=[
                                    coding.Coding(
                                        system=(
                                            SYSTEM.claim_item_category_pmjy
                                            if item["category"] == "HBP"
                                            else SYSTEM.claim_item_category
                                        ),
                                        code=item["category"],
                                    )
                                ]
                            ),
                        )
                    ),
                    items,
                    range(1, len(items) + 1),
                )
            ),
            supportingInfo=list(
                map(
                    lambda info, i: (
                        claim.ClaimSupportingInfo(
                            sequence=i,
                            category=codeableconcept.CodeableConcept(
                                coding=[
                                    coding.Coding(
                                        system=SYSTEM.claim_supporting_info_category,
                                        code=info["type"],
                                    )
                                ]
                            ),
                            valueAttachment=attachment.Attachment(
                                url=info["url"],
                                title=info["name"],
                            ),
                        )
                    ),
                    supporting_info,
                    range(1, len(supporting_info) + 1),
                )
            ),
            procedure=list(
                map(
                    lambda procedure, i: (
                        claim.ClaimProcedure(
                            sequence=i,
                            procedureReference=reference.Reference(
                                reference=self.get_reference_url(procedure)
                            ),
                        )
                    ),
                    procedures,
                    range(1, len(procedures) + 1),
                )
            ),
            diagnosis=list(
                map(
                    lambda diagnosis, i: (
                        claim.ClaimDiagnosis(
                            sequence=i,
                            diagnosisReference=reference.Reference(
                                reference=self.get_reference_url(diagnosis["profile"])
                            ),
                            type=[
                                codeableconcept.CodeableConcept(
                                    coding=[
                                        coding.Coding(
                                            system=SYSTEM.diagnosis_type,
                                            code=diagnosis["type"],
                                        )
                                    ]
                                )
                            ],
                        )
                    ),
                    diagnoses,
                    range(1, len(diagnoses) + 1),
                )
            ),
        )

    def create_procedure_profile(
        self,
        id,
        name,
        patient,
        provider,
        status="unknown",
        performed=None,
    ):
        return procedure.Procedure(
            id=id,
            # meta=meta.Meta(
            #     profile=[PROFILE.procedure],
            # ),
            status=status,
            note=[annotation.Annotation(text=name)],
            subject=reference.Reference(reference=self.get_reference_url(patient)),
            performer=[
                procedure.ProcedurePerformer(
                    actor=reference.Reference(
                        reference=self.get_reference_url(provider)
                    )
                )
            ],
            performedString=performed,
        )

    def create_condition_profile(self, id, code, label, patient):
        return condition.Condition(
            id=id,
            # meta=meta.Meta(profile=[PROFILE.condition]),
            code=codeableconcept.CodeableConcept(
                coding=[
                    coding.Coding(system=SYSTEM.condition, code=code, display=label)
                ]
            ),
            subject=reference.Reference(reference=self.get_reference_url(patient)),
        )

    def create_coverage_eligibility_request_bundle(
        self,
        id: str,
        identifier_value: str,
        provider_id: str,
        provider_name: str,
        provider_identifier_value: str,
        insurer_id: str,
        insurer_name: str,
        insurer_identifier_value: str,
        enterer_id: str,
        enterer_identifier_value: str,
        enterer_speciality: str,
        enterer_phone: str,
        patient_id: str,
        pateint_name: str,
        patient_gender: Literal["male", "female", "other", "unknown"],
        subscriber_id: str,
        policy_id: str,
        coverage_id: str,
        eligibility_request_id: str,
        eligibility_request_identifier_value: str,
        patient_phone: str,
        status="active",
        priority="normal",
        purpose="validation",
        service_period_start=datetime.now().astimezone(tz=timezone.utc),
        service_period_end=datetime.now().astimezone(tz=timezone.utc),
        last_upadted=datetime.now().astimezone(tz=timezone.utc),
    ):
        provider = self.create_provider_profile(
            provider_id, provider_name, provider_identifier_value
        )
        insurer = self.create_insurer_profile(
            insurer_id, insurer_name, insurer_identifier_value
        )
        patient = self.create_patient_profile(
            patient_id, pateint_name, patient_gender, patient_phone, subscriber_id
        )
        enterer = self.create_practitioner_role_profile(
            enterer_id, enterer_identifier_value, enterer_speciality, enterer_phone
        )
        coverage = self.create_coverage_profile(
            coverage_id,
            policy_id,
            subscriber_id,
            patient,
            insurer,
            status,
        )
        coverage_eligibility_request = self.create_coverage_eligibility_request_profile(
            eligibility_request_id,
            eligibility_request_identifier_value,
            patient,
            enterer,
            provider,
            insurer,
            coverage,
            priority,
            status,
            purpose,
            service_period_start,
            service_period_end,
        )

        return bundle.Bundle(
            id=id,
            meta=meta.Meta(
                lastUpdated=last_upadted,
                profile=[PROFILE.coverage_eligibility_request_bundle],
            ),
            identifier=identifier.Identifier(
                system=SYSTEM.coverage_eligibility_request_bundle_identifier,
                value=identifier_value,
            ),
            type="collection",
            timestamp=datetime.now().astimezone(tz=timezone.utc),
            entry=[
                bundle.BundleEntry(
                    fullUrl=self.get_reference_url(coverage_eligibility_request),
                    resource=coverage_eligibility_request,
                ),
                bundle.BundleEntry(
                    fullUrl=self.get_reference_url(provider),
                    resource=provider,
                ),
                bundle.BundleEntry(
                    fullUrl=self.get_reference_url(insurer),
                    resource=insurer,
                ),
                bundle.BundleEntry(
                    fullUrl=self.get_reference_url(patient),
                    resource=patient,
                ),
                bundle.BundleEntry(
                    fullUrl=self.get_reference_url(coverage),
                    resource=coverage,
                ),
            ],
        )

    def create_claim_bundle(
        self,
        id: str,
        identifier_value: str,
        provider_id: str,
        provider_name: str,
        provider_identifier_value: str,
        insurer_id: str,
        insurer_name: str,
        insurer_identifier_value: str,
        patient_id: str,
        pateint_name: str,
        patient_gender: Literal["male", "female", "other", "unknown"],
        subscriber_id: str,
        policy_id: str,
        coverage_id: str,
        claim_id: str,
        claim_identifier_value: str,
        items: list[IClaimItem],
        patient_phone: str,
        use="claim",
        status="active",
        type="institutional",
        priority="normal",
        claim_payee_type="provider",
        last_updated=datetime.now().astimezone(tz=timezone.utc),
        supporting_info=[],
        related_claims=[],
        procedures=[],
        diagnoses=[],
    ):
        provider = self.create_provider_profile(
            provider_id, provider_name, provider_identifier_value
        )
        insurer = self.create_insurer_profile(
            insurer_id, insurer_name, insurer_identifier_value
        )
        patient = self.create_patient_profile(
            patient_id, pateint_name, patient_gender, patient_phone, subscriber_id
        )
        coverage = self.create_coverage_profile(
            coverage_id,
            policy_id,
            subscriber_id,
            patient,
            insurer,
            status,
        )

        procedures = list(
            map(
                lambda procedure: self.create_procedure_profile(
                    procedure["id"],
                    procedure["name"],
                    patient,
                    provider,
                    procedure["status"],
                    procedure["performed"],
                ),
                procedures,
            )
        )

        diagnoses = list(
            map(
                lambda diagnosis: {
                    "profile": self.create_condition_profile(
                        diagnosis["id"], diagnosis["code"], diagnosis["label"], patient
                    ),
                    "type": diagnosis["type"],
                },
                diagnoses,
            )
        )

        claim = self.create_claim_profile(
            claim_id,
            claim_identifier_value,
            items,
            patient,
            provider,
            insurer,
            coverage,
            use,
            status,
            type,
            priority,
            claim_payee_type,
            supporting_info=supporting_info,
            related_claims=related_claims,
            procedures=procedures,
            diagnoses=diagnoses,
        )

        return bundle.Bundle(
            id=id,
            meta=meta.Meta(
                lastUpdated=last_updated,
                profile=[PROFILE.claim_bundle],
            ),
            identifier=identifier.Identifier(
                system=SYSTEM.claim_bundle_identifier,
                value=identifier_value,
            ),
            type="collection",
            timestamp=datetime.now().astimezone(tz=timezone.utc),
            entry=[
                bundle.BundleEntry(
                    fullUrl=self.get_reference_url(claim),
                    resource=claim,
                ),
                bundle.BundleEntry(
                    fullUrl=self.get_reference_url(provider),
                    resource=provider,
                ),
                bundle.BundleEntry(
                    fullUrl=self.get_reference_url(insurer),
                    resource=insurer,
                ),
                bundle.BundleEntry(
                    fullUrl=self.get_reference_url(patient),
                    resource=patient,
                ),
                bundle.BundleEntry(
                    fullUrl=self.get_reference_url(coverage),
                    resource=coverage,
                ),
                *list(
                    map(
                        lambda procedure: bundle.BundleEntry(
                            fullUrl=self.get_reference_url(procedure),
                            resource=procedure,
                        ),
                        procedures,
                    )
                ),
                *list(
                    map(
                        lambda diagnosis: bundle.BundleEntry(
                            fullUrl=self.get_reference_url(diagnosis["profile"]),
                            resource=diagnosis["profile"],
                        ),
                        diagnoses,
                    )
                ),
            ],
        )

    def create_communication_profile(
        self,
        id: str,
        identifier_value: str,
        payload: list,
        about: list,
        last_updated=datetime.now().astimezone(tz=timezone.utc),
    ):
        return communication.Communication(
            id=id,
            identifier=[
                identifier.Identifier(
                    system=SYSTEM.communication_identifier, value=identifier_value
                )
            ],
            meta=meta.Meta(lastUpdated=last_updated, profile=[PROFILE.communication]),
            status="completed",
            about=list(
                map(
                    lambda ref: (reference.Reference(type=ref["type"], id=ref["id"])),
                    about,
                )
            ),
            payload=list(
                map(
                    lambda content: (
                        communication.CommunicationPayload(
                            contentString=(
                                content["data"] if content["type"] == "text" else None
                            ),
                            contentAttachment=(
                                attachment.Attachment(
                                    url=content["data"],
                                    title=content["name"] if content["name"] else None,
                                )
                                if content["type"] == "url"
                                else None
                            ),
                        )
                    ),
                    payload,
                )
            ),
        )

    def create_communication_bundle(
        self,
        id: str,
        identifier_value: str,
        communication_id: str,
        communication_identifier_value: str,
        payload: list,
        about: list,
        last_updated=datetime.now().astimezone(tz=timezone.utc),
    ):
        communication_profile = self.create_communication_profile(
            communication_id,
            communication_identifier_value,
            payload,
            about,
            last_updated,
        )

        return bundle.Bundle(
            id=id,
            meta=meta.Meta(
                lastUpdated=last_updated,
                profile=[PROFILE.communication_bundle],
            ),
            identifier=identifier.Identifier(
                system=SYSTEM.communication_bundle_identifier,
                value=identifier_value,
            ),
            type="collection",
            timestamp=datetime.now().astimezone(tz=timezone.utc),
            entry=[
                bundle.BundleEntry(
                    fullUrl=self.get_reference_url(communication_profile),
                    resource=communication_profile,
                ),
            ],
        )

    def process_coverage_elibility_check_response(self, response):
        coverage_eligibility_check_bundle = bundle.Bundle(**response)

        coverage_eligibility_check_response = (
            coverageeligibilityresponse.CoverageEligibilityResponse(
                **list(
                    filter(
                        lambda entry: entry.resource
                        is coverageeligibilityresponse.CoverageEligibilityResponse,
                        coverage_eligibility_check_bundle.entry,
                    )
                )[0].resource.dict()
            )
        )
        coverage_request = coverage.Coverage(
            **list(
                filter(
                    lambda entry: entry.resource is coverage.Coverage,
                    coverage_eligibility_check_bundle.entry,
                )
            )[0].resource.dict()
        )

        def get_errors_from_coding(codings):
            return "; ".join(
                list(map(lambda coding: f"{coding.code}: {coding.display}", codings))
            )

        return {
            "id": coverage_request.id,
            "outcome": coverage_eligibility_check_response.outcome,
            "error": ", ".join(
                list(
                    map(
                        lambda error: get_errors_from_coding(error.code.coding),
                        coverage_eligibility_check_response.error or [],
                    )
                )
            ),
        }

    def process_claim_response(self, response):
        claim_bundle = bundle.Bundle(**response)

        claim_response = claimresponse.ClaimResponse(
            **list(
                filter(
                    lambda entry: entry.resource is claimresponse.ClaimResponse,
                    claim_bundle.entry,
                )
            )[0].resource.dict()
        )

        def get_errors_from_coding(codings):
            return "; ".join(
                list(map(lambda coding: f"{coding.code}: {coding.display}", codings))
            )

        return {
            "id": claim_bundle.id,
            "total_approved": reduce(
                lambda price, acc: price + acc,
                map(
                    lambda claim_response_total: float(
                        claim_response_total.amount.value
                    ),
                    claim_response.total,
                ),
                0.0,
            ),
            "outcome": claim_response.outcome,
            "error": ", ".join(
                list(
                    map(
                        lambda error: get_errors_from_coding(error.code.coding),
                        claim_response.error or [],
                    )
                )
            ),
        }

    def process_communication_request(self, request):
        communication_request = communicationrequest.CommunicationRequest(**request)

        data = {
            "identifier": communication_request.id
            or communication_request.identifier[0].value,
            "status": communication_request.status,
            "priority": communication_request.priority,
            "about": None,
            "based_on": None,
            "payload": None,
        }

        if communication_request.about:
            data["about"] = []
            for object in communication_request.about:
                about = reference.Reference(**object.dict())
                if about.identifier:
                    id = identifier.Identifier(about.identifier).value
                    data["about"].append(id)
                    continue

                if about.reference:
                    id = about.reference.split("/")[-1]
                    data["about"].append(id)
                    continue

        if communication_request.basedOn:
            data["based_on"] = []
            for object in communication_request.basedOn:
                based_on = reference.Reference(**object.dict())
                if based_on.identifier:
                    id = identifier.Identifier(based_on.identifier).value
                    data["based_on"].append(id)
                    continue

                if based_on.reference:
                    id = based_on.reference.split("/")[-1]
                    data["based_on"].append(id)
                    continue

        if communication_request.payload:
            data["payload"] = []
            for object in communication_request.payload:
                payload = communicationrequest.CommunicationRequestPayload(
                    **object.dict()
                )

                if payload.contentString:
                    data["payload"].append(
                        {"type": "text", "data": payload.contentString}
                    )
                    continue

                if payload.contentAttachment:
                    content = attachment.Attachment(payload.contentAttachment)
                    if content.data:
                        data["payload"].append(
                            {
                                "type": content.contentType or "text",
                                "data": content.data,
                            }
                        )
                    elif content.url:
                        data["payload"].append({"type": "url", "data": content.url})

        return data

    def validate_fhir_local(self, fhir_payload, type="bundle"):
        try:
            if type == "bundle":
                bundle.Bundle(**fhir_payload)
        except Exception as e:
            return {"valid": False, "issues": [e]}

        return {"valid": True, "issues": None}

    def validate_fhir_remote(self, fhir_payload):
        headers = {"Content-Type": "application/json"}
        response = requests.request(
            "POST", FHIR_VALIDATION_URL, headers=headers, data=fhir_payload
        ).json()

        issues = response["issue"] if "issue" in response else []
        valid = True

        for issue in issues:
            if issue["severity"] == "error":
                valid = False
                break

        return {"valid": valid, "issues": issues}
