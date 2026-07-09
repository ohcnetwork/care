"""BAP receiver endpoint for the Care-as-BAP resource-request referral flow.

When Care initiates an outbound ``confirm`` to an external coordination center
(CC, acting as BPP) for a ``pending``/``other`` resource request, the CC
processes it and posts an ``on_confirm`` callback back to this endpoint (the
configured ``BECKN_BAP_URI``).

Correlation uses the Beckn ``transactionId``, which Care set to the resource
request's ``external_id`` when sending the confirm. On an ``on_confirm`` whose
``message.contract.status.code`` is ``ACTIVE``, the resource request is moved
from ``pending`` to ``approved``.

Authentication is intentionally open (the network layer verifies signatures);
deployments should additionally restrict access by network/IP.
"""

import json
import logging

from rest_framework import status as http_status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from care.beckn.constants import CONTRACT_STATUS_ACTIVE
from care.beckn.mappers import extract_health_ids, find_patient_participant
from care.beckn.services.identifiers import attach_abha_identifier
from care.emr.models.resource_request import ResourceRequest
from care.emr.resources.resource_request.spec import CategoryChoices, StatusChoices

logger = logging.getLogger(__name__)


def _ack() -> dict:
    return {"message": {"ack": {"status": "ACK"}}}


def _nack(code: str, message: str) -> dict:
    return {
        "message": {"ack": {"status": "NACK"}},
        "error": {"type": "DOMAIN-ERROR", "code": code, "message": message},
    }


class BAPReceiverView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        body = request.data or {}
        context = body.get("context", {}) or {}
        message = body.get("message", {}) or {}
        action = kwargs.get("action") or context.get("action")
        transaction_id = context.get("transactionId")

        logger.info(
            "Beckn BAP receiver <- '%s' (transactionId=%s)\nbody=%s",
            action,
            transaction_id,
            json.dumps(body, default=str)[:2000],
        )

        if not transaction_id:
            return Response(
                _nack("70001", "Missing transactionId"),
                status=http_status.HTTP_200_OK,
            )

        resource_request = ResourceRequest.objects.filter(
            external_id=transaction_id,
            category__in=(
                CategoryChoices.other.value,
                CategoryChoices.patient_care.value,
            ),
        ).first()
        if resource_request is None:
            logger.warning(
                "Beckn BAP receiver: no resource request for transaction %s",
                transaction_id,
            )
            return Response(
                _nack("70002", "Unknown transaction"),
                status=http_status.HTTP_200_OK,
            )

        if action == "on_confirm":
            self._handle_on_confirm(resource_request, message)

        return Response(_ack(), status=http_status.HTTP_200_OK)

    @staticmethod
    def _handle_on_confirm(resource_request, message: dict) -> None:
        contract = (message or {}).get("contract", {}) or {}
        code = ((contract.get("status", {}) or {}).get("code") or "").upper()
        if (
            code == CONTRACT_STATUS_ACTIVE
            and resource_request.status == StatusChoices.pending.value
        ):
            resource_request.status = StatusChoices.approved.value
            resource_request.save(update_fields=["status", "modified_date"])
            BAPReceiverView._record_abha_identifier(resource_request, message)
            logger.info(
                "Beckn on_confirm approved resource request %s (status -> approved)",
                resource_request.external_id,
            )
        else:
            logger.info(
                "Beckn on_confirm no-op for resource request %s "
                "(contract.status=%s, current status=%s)",
                resource_request.external_id,
                code,
                resource_request.status,
            )

    @staticmethod
    def _record_abha_identifier(resource_request, message: dict) -> None:
        """Persist the patient's ABHA number carried on the ``on_confirm``."""
        patient = resource_request.related_patient
        if patient is None:
            return
        participant = find_patient_participant(message)
        health_ids = extract_health_ids(participant)
        attach_abha_identifier(patient, health_ids)
