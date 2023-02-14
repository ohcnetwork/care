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
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.period import Period
from datetime import datetime, timezone
from uuid import uuid4 as uuid


# TODO: seperate out system in coding and profile into a const dict


def get_reference(resource: DomainResource):
    return f"{resource.resource_type}/{resource.id}"


def create_organization_hospital(id, name, hfr_id):
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
                            display="Narayana",  # what is this value?
                        )
                    ]
                },
                system="http://abdm.gov.in/facilities",
                value=hfr_id,
            )
        ],
        name=name,
    )


def create_organization_insurer(id="GICOFINDIA", name="GICOFINDIA"):
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


def create_patient(id, name, gender, subscriber_number):
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


def create_coverage(id, policy_id, subscriber_number, patient, insurer):
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
def create_coverage_eligibility_request(
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
            Identifier(
                value="req_70e02576-f5f5-424f-b115-b5f1029704d4"  # what is this?
            )
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
        purpose=["benefits"],  # can this be hard coded?
        patient=Reference(reference=get_reference(patient)),
        servicedPeriod=Period(
            start=datetime.now().astimezone(tz=timezone.utc),
            end=datetime.now().astimezone(tz=timezone.utc),
        ),
        created=datetime.now().astimezone(tz=timezone.utc),
        enterer=Reference(reference="http://abcd.com/Tmh01"),  # what is this?
        provider=Reference(reference=get_reference(insurer)),
        insurer=Reference(reference=get_reference(hospital)),  # is these 2 correct?
        facility=Reference(
            reference="http://sgh.com.sa/Location/4461281"
        ),  # what is this?
        insurance=[
            CoverageEligibilityRequestInsurance(
                coverage=Reference(reference=get_reference(coverage))
            )
        ],
    )


def create_coverage_eligibility_request_bundle(
    id, hospital, insurer, patient, coverage
):
    coverage_eligibility_request = create_coverage_eligibility_request(
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

    hospital = create_organization_hospital(hospital_id, hospital_name, hospital_hrf_id)
    insurer = create_organization_insurer()
    patient = create_patient(
        patient_id, patient_name, patient_gender, policy_subscriber_number
    )
    coverage = create_coverage(
        str(uuid()), policy_policy_id, policy_subscriber_number, patient, insurer
    )
    coverage_eligibility_request = create_coverage_eligibility_request_bundle(
        str(uuid()), hospital, insurer, patient, coverage
    )

    return coverage_eligibility_request
