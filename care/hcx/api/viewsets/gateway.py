from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from care.hcx.models.policy import Policy
from care.hcx.models.claim import Claim
from care.facility.models.patient_consultation import PatientConsultation
from care.hcx.api.serializers.gateway import (
    CheckEligibilitySerializer,
    MakeClaimSerializer,
)
from care.hcx.api.serializers.policy import PolicySerializer
from care.hcx.api.serializers.claim import ClaimSerializer
from care.hcx.utils.fhir import Fhir
from care.facility.models.file_upload import FileUpload
from care.facility.tasks.patient.discharge_report import (
    generate_discharge_report_signed_url,
)
from uuid import uuid4 as uuid
from care.hcx.utils.hcx import Hcx, HcxOperations
import json
from datetime import datetime
from drf_yasg.utils import swagger_auto_schema
from care.users.models import User
from care.hcx.models.base import (
    REVERSE_CLAIM_TYPE_CHOICES,
    REVERSE_PRIORITY_CHOICES,
    REVERSE_PURPOSE_CHOICES,
    REVERSE_STATUS_CHOICES,
    REVERSE_USE_CHOICES,
)
from care.facility.static_data.icd11 import ICDDiseases
from django.db.models import Q
from re import IGNORECASE


class HcxGatewayViewSet(GenericViewSet):
    queryset = Policy.objects.all()

    @swagger_auto_schema(tags=["hcx"], request_body=CheckEligibilitySerializer())
    @action(detail=False, methods=["post"])
    def check_eligibility(self, request):
        data = request.data

        serializer = CheckEligibilitySerializer(data=data)
        serializer.is_valid(raise_exception=True)

        policy = PolicySerializer(self.queryset.get(external_id=data["policy"])).data

        eligibility_check_fhir_bundle = (
            Fhir().create_coverage_eligibility_request_bundle(
                policy["id"],
                policy["policy_id"],
                policy["patient_object"]["facility_object"]["id"],
                policy["patient_object"]["facility_object"]["name"],
                "IN000018",
                "GICOFINDIA",
                "GICOFINDIA",
                "GICOFINDIA",
                policy["last_modified_by"]["username"],
                policy["last_modified_by"]["username"],
                "223366009",
                "7894561232",
                policy["patient_object"]["id"],
                policy["patient_object"]["name"],
                "male"
                if policy["patient_object"]["gender"] == 1
                else "female"
                if policy["patient_object"]["gender"] == 2
                else "other",
                policy["subscriber_id"],
                policy["policy_id"],
                policy["id"],
                policy["id"],
                policy["id"],
                REVERSE_STATUS_CHOICES[policy["status"]],
                REVERSE_PRIORITY_CHOICES[policy["priority"]],
                REVERSE_PURPOSE_CHOICES[policy["purpose"]],
            )
        )

        if not Fhir().validate_fhir_remote(eligibility_check_fhir_bundle.json())[
            "valid"
        ]:
            return Response(
                {"message": "Invalid FHIR object"}, status=status.HTTP_400_BAD_REQUEST
            )

        response = Hcx().generateOutgoingHcxCall(
            fhirPayload=json.loads(eligibility_check_fhir_bundle.json()),
            operation=HcxOperations.COVERAGE_ELIGIBILITY_CHECK,
            recipientCode="1-29482df3-e875-45ef-a4e9-592b6f565782",
        )

        return Response(dict(response.get("response")), status=status.HTTP_200_OK)

    @swagger_auto_schema(tags=["hcx"], request_body=MakeClaimSerializer())
    @action(detail=False, methods=["post"])
    def make_claim(self, request):
        data = request.data

        serializer = MakeClaimSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        claim = ClaimSerializer(Claim.objects.get(external_id=data["claim"])).data
        consultation = PatientConsultation.objects.get(
            external_id=claim["consultation_object"]["id"]
        )

        procedures = []
        if len(consultation.procedure):
            procedures = list(
                map(
                    lambda procedure: {
                        "id": str(uuid()),
                        "name": procedure["procedure"],
                        "performed": procedure["time"]
                        if "time" in procedure
                        else procedure["frequency"],
                        "status": (
                            "completed"
                            if datetime.strptime(procedure["time"], "%Y-%m-%dT%H:%M")
                            < datetime.now()
                            else "preparation"
                        )
                        if "time" in procedure
                        else "in-progress",
                    },
                    consultation.procedure,
                )
            )

        diagnoses = []
        if len(consultation.icd11_diagnoses):
            diagnoses = list(
                map(
                    lambda diagnosis: {
                        "id": str(uuid()),
                        "label": diagnosis.label.split(" ", 1)[1],
                        "code": diagnosis.label.split(" ", 1)[0] or "00",
                        "type": "clinical",
                    },
                    list(
                        map(
                            lambda icd_id: ICDDiseases.by.id[icd_id],
                            consultation.icd11_diagnoses,
                        )
                    ),
                )
            )

        if len(consultation.icd11_provisional_diagnoses):
            diagnoses = list(
                map(
                    lambda diagnosis: {
                        "id": str(uuid()),
                        "label": diagnosis.label.split(" ", 1)[1],
                        "code": diagnosis.label.split(" ", 1)[0] or "00",
                        "type": "admitting",
                    },
                    list(
                        map(
                            lambda icd_id: ICDDiseases.by.id[icd_id],
                            consultation.icd11_provisional_diagnoses,
                        )
                    ),
                )
            )

        previous_claim = (
            Claim.objects.filter(
                consultation__external_id=claim["consultation_object"]["id"]
            )
            .order_by("-modified_date")
            .exclude(external_id=claim["id"])
            .first()
        )
        related_claims = []
        if previous_claim:
            related_claims.append(
                {"id": str(previous_claim.external_id), "type": "prior"}
            )

        docs = list(
            map(
                lambda file: (
                    {"type": "MB", "name": file.name, "url": file.read_signed_url()}
                ),
                FileUpload.objects.filter(
                    Q(associating_id=claim["consultation_object"]["id"])
                    | Q(associating_id=claim["id"])
                ),
            )
        )

        if REVERSE_USE_CHOICES[claim["use"]] == "claim":
            discharge_summary_url = generate_discharge_report_signed_url(
                claim["policy_object"]["patient_object"]["id"]
            )
            docs.append(
                {
                    "type": "DIA",
                    "name": "Discharge Summary",
                    "url": discharge_summary_url,
                }
            )

        claim_fhir_bundle = Fhir().create_claim_bundle(
            claim["id"],
            claim["id"],
            claim["policy_object"]["patient_object"]["facility_object"]["id"],
            claim["policy_object"]["patient_object"]["facility_object"]["name"],
            "IN000018",
            "GICOFINDIA",
            "GICOFINDIA",
            "GICOFINDIA",
            claim["policy_object"]["patient_object"]["id"],
            claim["policy_object"]["patient_object"]["name"],
            "male"
            if claim["policy_object"]["patient_object"]["gender"] == 1
            else "female"
            if claim["policy_object"]["patient_object"]["gender"] == 2
            else "other",
            claim["policy_object"]["subscriber_id"],
            claim["policy_object"]["policy_id"],
            claim["policy_object"]["id"],
            claim["id"],
            claim["id"],
            claim["items"],
            REVERSE_USE_CHOICES[claim["use"]],
            REVERSE_STATUS_CHOICES[claim["status"]],
            REVERSE_CLAIM_TYPE_CHOICES[claim["type"]],
            REVERSE_PRIORITY_CHOICES[claim["priority"]],
            supporting_info=docs,
            related_claims=related_claims,
            procedures=procedures,
            diagnoses=diagnoses,
        )

        if not Fhir().validate_fhir_remote(claim_fhir_bundle.json())["valid"]:
            return Response(
                {"message": "Invalid FHIR object"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = Hcx().generateOutgoingHcxCall(
            fhirPayload=json.loads(claim_fhir_bundle.json()),
            operation=HcxOperations.CLAIM_SUBMIT
            if REVERSE_USE_CHOICES[claim["use"]] == "claim"
            else HcxOperations.PRE_AUTH_SUBMIT,
            recipientCode="1-29482df3-e875-45ef-a4e9-592b6f565782",
        )

        return Response(dict(response.get("response")), status=status.HTTP_200_OK)

    @swagger_auto_schema(tags=["hcx"])
    @action(detail=False, methods=["get"])
    def payors(self, request):
        payors = Hcx().searchRegistry("roles", "payor")["participants"]

        active_payors = list(filter(lambda payor: payor["status"] == "Active", payors))

        response = list(
            map(
                lambda payor: {
                    "name": payor["participant_name"],
                    "code": payor["participant_code"],
                },
                active_payors,
            )
        )

        return Response(response, status=status.HTTP_200_OK)

    @swagger_auto_schema(tags=["hcx"])
    @action(detail=False, methods=["get"])
    def pmjy_packages(self, request):
        from care.hcx.static_data.pmjy_packages import PMJYPackages

        def serailize_data(pmjy_packages):
            result = []
            for pmjy_package in pmjy_packages:
                if type(pmjy_package) == tuple:
                    pmjy_package = pmjy_package[0]
                result.append(
                    {
                        "code": pmjy_package.code,
                        "name": pmjy_package.name,
                        "price": pmjy_package.price,
                        "package_name": pmjy_package.package_name,
                    }
                )
            return result

        queryset = PMJYPackages
        limit = request.GET.get("limit", 20)
        if request.GET.get("query", False):
            query = request.GET.get("query")
            queryset = queryset.where(
                name=queryset.re_match(r".*" + query + r".*", IGNORECASE)
            )
        return Response(serailize_data(queryset[0:limit]))
