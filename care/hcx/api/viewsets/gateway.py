from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from care.hcx.models.policy import Policy
from care.hcx.api.serializers.gateway import CheckEligibilitySerializer
from care.hcx.api.serializers.policy import PolicySerializer
from care.hcx.utils.fhir import eligibility_check_fhir


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
