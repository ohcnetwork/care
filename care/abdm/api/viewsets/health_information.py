import json
import logging

from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.abdm.models.consent import ConsentArtefact
from care.abdm.service.gateway import Gateway
from care.abdm.utils.cipher import Cipher
from care.facility.models.file_upload import FileUpload
from config.auth_views import CaptchaRequiredException
from config.authentication import ABDMAuthentication
from config.ratelimit import USER_READABLE_RATE_LIMIT_TIME, ratelimit

logger = logging.getLogger(__name__)


class HealthInformationViewSet(GenericViewSet):
    permission_classes = (IsAuthenticated,)

    def retrieve(self, request, pk):
        files = FileUpload.objects.filter(
            Q(internal_name__contains=f"{pk}.json") | Q(associating_id=pk),
            file_type=FileUpload.FileType.ABDM_HEALTH_INFORMATION.value,
            upload_completed=True,
        )

        if files.count() == 0:
            return Response(
                {"detail": "No Health Information found for the given id"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if files.count() == 1 and files.first().is_archived:
            return Response(
                {
                    "is_archived": True,
                    "archived_reason": files.first().archive_reason,
                    "archived_time": files.first().archived_datetime,
                    "detail": f"This file has been archived as { files.first().archive_reason} at { files.first().archived_datetime}",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        files = files.filter(is_archived=False)

        contents = []
        for file in files:
            _, content = file.file_contents()
            contents.extend(content)

        return Response({"data": json.loads(content)}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["POST"])
    def request(self, request, pk):
        if ratelimit(request, "health_information__request", [pk]):
            raise CaptchaRequiredException(
                detail={
                    "status": 429,
                    "detail": f"Request limit reached. Try after {USER_READABLE_RATE_LIMIT_TIME}",
                },
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        artefact = ConsentArtefact.objects.filter(external_id=pk).first()

        if not artefact:
            return Response(
                {"detail": "No Consent artefact found with the given id"},
                status=status.HTTP_404_NOT_FOUND,
            )

        response = Gateway().health_information__cm__request(artefact)
        if response.status_code != 202:
            return Response(response.json(), status=response.status_code)

        return Response(status=status.HTTP_200_OK)


class HealthInformationCallbackViewSet(GenericViewSet):
    permission_classes = (IsAuthenticated,)
    authentication_classes = [ABDMAuthentication]

    def health_information__hiu__on_request(self, request):
        data = request.data

        artefact = ConsentArtefact.objects.filter(
            consent_id=data["resp"]["requestId"]
        ).first()

        if not artefact:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if "hiRequest" in data:
            artefact.consent_id = data["hiRequest"]["transactionId"]
            artefact.save()

        return Response(status=status.HTTP_202_ACCEPTED)

    def health_information__transfer(self, request):
        data = request.data

        artefact = ConsentArtefact.objects.filter(
            consent_id=data["transactionId"]
        ).first()

        if not artefact:
            return Response(status=status.HTTP_404_NOT_FOUND)

        cipher = Cipher(
            data["keyMaterial"]["dhPublicKey"]["keyValue"],
            data["keyMaterial"]["nonce"],
            artefact.key_material_private_key,
            artefact.key_material_public_key,
            artefact.key_material_nonce,
        )
        entries = []
        for entry in data["entries"]:
            if "content" in entry:
                entries.append(
                    {
                        "content": cipher.decrypt(entry["content"]),
                        "care_context_reference": entry["careContextReference"],
                    }
                )

            if "link" in entry:
                # TODO: handle link
                pass

        file = FileUpload(
            internal_name=f"{artefact.external_id}.json",
            file_type=FileUpload.FileType.ABDM_HEALTH_INFORMATION.value,
            associating_id=artefact.consent_request.external_id,
        )
        file.put_object(json.dumps(entries), ContentType="application/json")
        file.upload_completed = True
        file.save()

        try:
            Gateway().health_information__notify(artefact)
        except Exception as e:
            logger.warning(
                f"Error: health_information__transfer::post failed to notify (health-information/notify). Reason: {e}",
                exc_info=True,
            )
            return Response(
                {"detail": "Failed to notify (health-information/notify)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_202_ACCEPTED)
