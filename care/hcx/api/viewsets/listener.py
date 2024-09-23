import json

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from care.hcx.models.claim import Claim
from care.hcx.models.communication import Communication
from care.hcx.models.policy import Policy
from care.hcx.utils.fhir import Fhir
from care.hcx.utils.hcx import Hcx
from care.utils.notification_handler import send_webpush


class CoverageElibilityOnCheckView(GenericAPIView):
    permission_classes = ()
    authentication_classes = ()

    @extend_schema(tags=["hcx"])
    def post(self, request, *args, **kwargs):
        response = Hcx().processIncomingRequest(request.data["payload"])
        data = Fhir().process_coverage_elibility_check_response(response["payload"])

        policy = Policy.objects.filter(external_id=data["id"]).first()
        policy.outcome = data["outcome"]
        policy.error_text = data["error"]
        policy.save()

        message = {
            "type": "MESSAGE",
            "from": "coverageelegibility/on_check",
            "message": "success" if not data["error"] else "failed",
        }
        send_webpush(
            username=policy.last_modified_by.username, message=json.dumps(message)
        )

        return Response({}, status=status.HTTP_202_ACCEPTED)


class PreAuthOnSubmitView(GenericAPIView):
    permission_classes = ()
    authentication_classes = ()

    @extend_schema(tags=["hcx"])
    def post(self, request, *args, **kwargs):
        response = Hcx().processIncomingRequest(request.data["payload"])
        data = Fhir().process_claim_response(response["payload"])

        claim = Claim.objects.filter(external_id=data["id"]).first()
        claim.outcome = data["outcome"]
        claim.total_amount_approved = data["total_approved"]
        claim.error_text = data["error"]
        claim.save()

        message = {
            "type": "MESSAGE",
            "from": "preauth/on_submit",
            "message": "success" if not data["error"] else "failed",
        }
        send_webpush(
            username=claim.last_modified_by.username, message=json.dumps(message)
        )

        return Response({}, status=status.HTTP_202_ACCEPTED)


class ClaimOnSubmitView(GenericAPIView):
    permission_classes = ()
    authentication_classes = ()

    @extend_schema(tags=["hcx"])
    def post(self, request, *args, **kwargs):
        response = Hcx().processIncomingRequest(request.data["payload"])
        data = Fhir().process_claim_response(response["payload"])

        claim = Claim.objects.filter(external_id=data["id"]).first()
        claim.outcome = data["outcome"]
        claim.total_amount_approved = data["total_approved"]
        claim.error_text = data["error"]
        claim.save()

        message = {
            "type": "MESSAGE",
            "from": "preauth/on_submit",
            "message": "success" if not data["error"] else "failed",
        }
        send_webpush(
            username=claim.last_modified_by.username, message=json.dumps(message)
        )

        return Response({}, status=status.HTTP_202_ACCEPTED)


class CommunicationRequestView(GenericAPIView):
    permission_classes = ()
    authentication_classes = ()

    @extend_schema(tags=["hcx"])
    def post(self, request, *args, **kwargs):
        response = Hcx().processIncomingRequest(request.data["payload"])
        data = Fhir().process_communication_request(response["payload"])

        claim = Claim.objects.filter(external_id__in=data["about"] or []).last()
        communication = Communication.objects.create(
            claim=claim,
            content=data["payload"],
            identifier=data[
                "identifier"
            ],  # TODO: replace identifier with corelation id
        )

        message = {
            "type": "MESSAGE",
            "from": "communication/request",
            "message": f"{communication.external_id}",
        }
        send_webpush(
            username=claim.last_modified_by.username, message=json.dumps(message)
        )

        return Response({}, status=status.HTTP_202_ACCEPTED)
