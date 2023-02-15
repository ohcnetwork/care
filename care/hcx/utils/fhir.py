from fhir.resources.meta import Meta
from fhir.resources.organization import Organization
from fhir.resources.identifier import Identifier
from fhir.resources.coding import Coding
from fhir.resources.patient import Patient
from fhir.resources.reference import Reference
from fhir.resources.coverage import Coverage
from fhir.resources.domainresource import DomainResource
from fhir.resources.fhirtypes import String
from fhir.resources.coverageeligibilityrequest import (
    CoverageEligibilityRequest,
    CoverageEligibilityRequestInsurance,
)
from fhir.resources.practitioner import Practitioner
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.period import Period
from fhir.resources.claim import (
    Claim,
    ClaimItem,
    ClaimCareTeam,
    ClaimPayee,
    ClaimInsurance,
)
from datetime import datetime, timezone
from uuid import uuid4 as uuid


# TODO: seperate out system in coding and profile into a const dict


def get_reference(resource: DomainResource):
    return f"{resource.resource_type}/{resource.id}"


def create_organization_profile_hospital(id, name, hfr_id):
    return Organization(
        id=id,
        meta=Meta(
            profile=["https://nrces.in/ndhm/fhir/r4/StructureDefinition/Organization"]
        ),
        identifier=[
            Identifier(
                type={
                    "coding": [
                        Coding(
                            system="http://terminology.hl7.org/CodeSystem/v2-0203",
                            code="AC",
                            display="Narayana",  # facility name
                        )
                    ]
                },
                system="http://abdm.gov.in/facilities",
                value=hfr_id,
            )
        ],
        name=name,
    )


def create_organization_profile_insurer(id="GICOFINDIA", name="GICOFINDIA"):
    return Organization(
        id=id,
        meta=Meta(
            profile=["https://nrces.in/ndhm/fhir/r4/StructureDefinition/Organization"]
        ),
        identifier=[
            Identifier(
                type={
                    "coding": [
                        Coding(
                            system="http://terminology.hl7.org/CodeSystem/v2-0203",
                            code="AC",
                            display="GOVOFINDIA",
                        )
                    ]
                },
                system="http://irdai.gov.in/insurers",
                value=id,
            )
        ],
        name=name,
    )


def create_patient_profile(id, name, gender, subscriber_number):
    return Patient(
        id=id,
        meta=Meta(
            profile=["https://nrces.in/ndhm/fhir/r4/StructureDefinition/Patient"]
        ),
        identifier=[
            Identifier(
                type={
                    "coding": [
                        Coding(
                            system="http://terminology.hl7.org/CodeSystem/v2-0203",
                            code="SN",
                            display="Subscriber Number",
                        )
                    ]
                },
                system="http://gicofIndia.com/beneficiaries",
                value=subscriber_number,
            )
        ],
        name=[{"text": name}],
        gender=gender,
    )


def create_coverage_profile(id, policy_id, subscriber_number, patient, insurer):
    return Coverage(
        id=id,
        meta=Meta(
            profile=[
                "https://ig.hcxprotocol.io/v0.7.1/StructureDefinition-Coverage.html"
            ]
        ),
        identifier=[
            Identifier(system="https://www.gicofIndia.in/policies", value=policy_id)
        ],
        status="active",
        subscriber=Reference(reference=get_reference(patient)),
        subscriberId=subscriber_number,
        beneficiary=Reference(reference=get_reference(patient)),
        relationship={
            "coding": [
                Coding(
                    system="http://terminology.hl7.org/CodeSystem/subscriber-relationship",
                    code="self",
                )
            ]
        },
        payor=[Reference(reference=get_reference(insurer))],
    )


# here insurer = govt of india, hospital = care_facility
def create_coverage_eligibility_request_profile(
    id, patient, hospital, insurer, coverage, priority="stat"
):
    return CoverageEligibilityRequest(
        id=id,
        meta=Meta(
            profile=[
                "https://ig.hcxprotocol.io/v0.7.1/StructureDefinition-CoverageEligibilityRequest.html"
            ]
        ),
        identifier=[
            Identifier(value="req_70e02576-f5f5-424f-b115-b5f1029704d4")  # local id
        ],
        status="active",
        priority={
            "coding": [
                Coding(
                    system="http://terminology.hl7.org/CodeSystem/processpriority",
                    code=priority,
                )
            ]
        },
        purpose=["benefits"],  # validation
        patient=Reference(reference=get_reference(patient)),
        servicedPeriod=Period(
            start=datetime.now().astimezone(tz=timezone.utc),
            end=datetime.now().astimezone(tz=timezone.utc),
        ),  # treatment period
        created=datetime.now().astimezone(tz=timezone.utc),
        enterer=Reference(reference="http://abcd.com/Tmh01"),  # nurse
        provider=Reference(reference=get_reference(hospital)),
        insurer=Reference(reference=get_reference(insurer)),
        insurance=[
            CoverageEligibilityRequestInsurance(
                coverage=Reference(reference=get_reference(coverage))
            )
        ],
    )


def create_coverage_eligibility_request_bundle(
    id, hospital, insurer, patient, coverage
):
    coverage_eligibility_request = create_coverage_eligibility_request_profile(
        str(uuid()), patient, hospital, insurer, coverage
    )
    return Bundle(
        id=id,
        meta=Meta(
            lastUpdated=datetime.now().astimezone(
                tz=timezone.utc
            ),  # where do we get this, or just the current time?
            profile=[
                "https://ig.hcxprotocol.io/v0.7.1/StructureDefinition-CoverageEligibilityRequestBundle.html"
            ],
        ),
        identifier=Identifier(
            system="https://www.tmh.in/bundle",
            value="49b04ec1-6353-44d6-ae0d-2cace958e96e",  # what is this and how is different from id?
        ),
        type="collection",
        timestamp=datetime.now().astimezone(tz=timezone.utc),
        entry=[
            BundleEntry(
                fullUrl=get_reference(coverage_eligibility_request),
                resource=coverage_eligibility_request,
            ),
            BundleEntry(
                fullUrl=get_reference(hospital),
                resource=hospital,
            ),
            BundleEntry(
                fullUrl=get_reference(insurer),
                resource=insurer,
            ),
            BundleEntry(
                fullUrl=get_reference(patient),
                resource=patient,
            ),
            BundleEntry(
                fullUrl=get_reference(coverage),
                resource=coverage,
            ),
        ],
    )


def eligibility_check_fhir(
    hospital_id,
    hospital_name,
    hospital_hrf_id,
    patient_id,
    patient_name,
    patient_gender,
    policy_subscriber_number,
    policy_policy_id,
):

    hospital = create_organization_profile_hospital(
        hospital_id, hospital_name, hospital_hrf_id
    )
    insurer = create_organization_profile_insurer()
    patient = create_patient_profile(
        patient_id, patient_name, patient_gender, policy_subscriber_number
    )
    coverage = create_coverage_profile(
        str(uuid()), policy_policy_id, policy_subscriber_number, patient, insurer
    )
    coverage_eligibility_request = create_coverage_eligibility_request_bundle(
        str(uuid()), hospital, insurer, patient, coverage
    )

    return coverage_eligibility_request


# item: id, name, price
def create_claim_profile(
    id,
    items,
    patient,
    hospital,
    insurer,
    coverage,
    use="claim",
    status="active",
    type="institutional",
    priority="normal",
):
    return Claim(
        id=id,
        meta=Meta(
            lastUpdated=datetime.now().astimezone(tz=timezone.utc),
            profile=["https://ig.hcxprotocol.io/v0.7.1/StructureDefinition-Claim.html"],
        ),
        identifier=[
            Identifier(system="http://identifiersystem.com", value="IdentifierValue")
        ],
        status=status,
        type={
            "coding": [
                Coding(
                    system="http://terminology.hl7.org/CodeSystem/claim-type", code=type
                )
            ]
        },
        use=use,
        patient=Reference(reference=get_reference(patient)),
        created=datetime.now().astimezone(tz=timezone.utc),
        insurer=Reference(reference=get_reference(insurer)),
        provider=Reference(reference=get_reference(hospital)),
        priority={
            "coding": [
                Coding(
                    system="http://terminology.hl7.org/CodeSystem/processpriority",
                    priority=priority,
                )
            ]
        },
        payee=ClaimPayee(
            type={
                "coding": [
                    Coding(
                        system="http://terminology.hl7.org/CodeSystem/payeetype",
                        code="provider",
                    )
                ]
            },
            party=Reference(reference=get_reference(hospital)),
        ),
        careTeam=[
            ClaimCareTeam(
                sequence=4,
                provider=Reference(reference=get_reference(hospital)),
            )
        ],
        insurance=[
            ClaimInsurance(
                sequence=1,
                focal=True,
                coverage=Reference(reference=get_reference(coverage)),
            )
        ],
        item=list(
            map(
                lambda item: (
                    ClaimItem(
                        sequence=1,
                        productOrService={
                            "coding": [
                                Coding(
                                    system="https://pmjay.gov.in/hbp-package-code",
                                    code=item["id"],
                                    display=item["name"],
                                )
                            ]
                        },
                        unitPrice={"value": item["price"], "currency": "INR"},
                    )
                ),
                items,
            )
        ),
    )


def create_claim_bundle(id, use, items, patient, hospital, insurer, coverage):
    claim = create_claim_profile(
        str(uuid()), items, patient, hospital, insurer, coverage, use
    )
    return Bundle(
        id=id,
        meta=Meta(
            lastUpdated=datetime.now().astimezone(tz=timezone.utc),
            profile=[
                "https://ig.hcxprotocol.io/v0.7.1/StructureDefinition-ClaimRequestBundle.html"
            ],
        ),
        identifier=Identifier(
            system="https://www.tmh.in/bundle",
            value="49b04ec1-6353-44d6-ae0d-2cace958e96e",
        ),
        type="collection",
        timestamp=datetime.now().astimezone(tz=timezone.utc),
        entry=[
            BundleEntry(
                fullUrl=get_reference(claim),
                resource=claim,
            ),
            BundleEntry(
                fullUrl=get_reference(hospital),
                resource=hospital,
            ),
            BundleEntry(
                fullUrl=get_reference(insurer),
                resource=insurer,
            ),
            BundleEntry(
                fullUrl=get_reference(patient),
                resource=patient,
            ),
            BundleEntry(
                fullUrl=get_reference(coverage),
                resource=coverage,
            ),
        ],
    )


def claim_fhir(
    hospital_id,
    hospital_name,
    hospital_hrf_id,
    patient_id,
    patient_name,
    patient_gender,
    policy_subscriber_number,
    policy_policy_id,
    use,
    items,
):
    hospital = create_organization_profile_hospital(
        hospital_id, hospital_name, hospital_hrf_id
    )
    insurer = create_organization_profile_insurer()
    patient = create_patient_profile(
        patient_id, patient_name, patient_gender, policy_subscriber_number
    )
    coverage = create_coverage_profile(
        str(uuid()), policy_policy_id, policy_subscriber_number, patient, insurer
    )
    claim_request = create_claim_bundle(
        str(uuid()), use, items, hospital, insurer, patient, coverage
    )

    return claim_request
