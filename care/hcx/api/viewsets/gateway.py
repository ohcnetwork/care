from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from care.hcx.models.policy import Policy
from care.hcx.models.claim import Claim
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
from care.hcx.utils.hcx import Hcx, HcxOperations
import json
from drf_yasg.utils import swagger_auto_schema
from care.users.models import User
from care.hcx.models.base import (
    REVERSE_CLAIM_TYPE_CHOICES,
    REVERSE_PRIORITY_CHOICES,
    REVERSE_PURPOSE_CHOICES,
    REVERSE_STATUS_CHOICES,
    REVERSE_USE_CHOICES,
)


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

        previous_claim = Claim.objects.order_by("-modified_date").first()

        docs = list(
            map(
                lambda file: ({"type": "MB", "url": file.read_signed_url()}),
                FileUpload.objects.filter(
                    associating_id=claim["consultation_object"]["id"]
                ),
            )
        )

        if REVERSE_USE_CHOICES[claim["use"]] == "claim":
            discharge_summary_url = generate_discharge_report_signed_url(
                claim["policy_object"]["patient_object"]["id"]
            )
            docs.append({"type": "DIA", "url": discharge_summary_url})

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
            claim["procedures"],
            REVERSE_USE_CHOICES[claim["use"]],
            REVERSE_STATUS_CHOICES[claim["status"]],
            REVERSE_CLAIM_TYPE_CHOICES[claim["type"]],
            REVERSE_PRIORITY_CHOICES[claim["priority"]],
            supporting_info=docs,
            related_claims=[{"id": str(previous_claim.external_id), "type": "prior"}],
        )

        # if not Fhir().validate_fhir_remote(claim_fhir_bundle.json())["valid"]:
        #     return Response(
        #         {"message": "Invalid FHIR object"},
        #         status=status.HTTP_400_BAD_REQUEST,
        #     )

        response = Hcx().generateOutgoingHcxCall(
            fhirPayload=json.loads(claim_fhir_bundle.json()),
            operation=HcxOperations.CLAIM_SUBMIT
            if REVERSE_USE_CHOICES[claim["use"]] == "claim"
            else HcxOperations.PRE_AUTH_SUBMIT,
            recipientCode="1-29482df3-e875-45ef-a4e9-592b6f565782",
        )

        return Response(dict(response.get("response")), status=status.HTTP_200_OK)
