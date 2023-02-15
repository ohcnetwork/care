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
from care.hcx.utils.fhir import eligibility_check_fhir, claim_fhir
from care.facility.models.patient import PatientRegistration


class HcxGatewayViewSet(GenericViewSet):
    queryset = Policy.objects.all()

    @action(detail=False, methods=["post"])
    def check_eligibility(self, request):
        data = request.data
        serializer = CheckEligibilitySerializer(data=data)
        serializer.is_valid(raise_exception=True)

        policy = PolicySerializer(self.queryset.get(external_id=data["policy"])).data

        eligibility_check_fhir_bundle = eligibility_check_fhir(
            policy["patient_object"]["facility_object"]["id"],
            policy["patient_object"]["facility_object"]["name"],
            "IN000018",
            policy["patient_object"]["id"],
            policy["patient_object"]["name"],
            "male" if policy["patient_object"]["gender"] == 1 else "female",
            policy["subscriber_id"],
            policy["policy_id"],
        )

        return Response(eligibility_check_fhir_bundle.dict(), status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def make_claim(self, request):
        data = request.data
        serializer = MakeClaimSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        claim = ClaimSerializer(Claim.objects.get(external_id=data["claim"])).data

        claim_fhir_bundle = claim_fhir(
            claim["policy_object"]["patient_object"]["facility_object"]["id"],
            claim["policy_object"]["patient_object"]["facility_object"]["name"],
            "IN000018",
            claim["policy_object"]["patient_object"]["id"],
            claim["policy_object"]["patient_object"]["name"],
            "male"
            if claim["policy_object"]["patient_object"]["gender"] == 1
            else "female",
            claim["policy_object"]["subscriber_id"],
            claim["policy_object"]["policy_id"],
            "claim",
            claim["procedures"],
        ).dict()

        return Response(claim_fhir_bundle, status=status.HTTP_200_OK)
