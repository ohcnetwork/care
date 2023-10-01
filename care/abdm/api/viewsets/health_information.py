from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.abdm.models.consent import ConsentArtefact
from care.abdm.service.gateway import Gateway
from care.abdm.utils.cipher import Cipher
from config.authentication import ABDMAuthentication


class HealthInformationViewSet(GenericViewSet):
    # TODO: add a endpoint to list the patients health information

    @action(detail=True, methods=["GET"])
    def request(self, request, pk):
        artefact = ConsentArtefact.objects.filter(external_id=pk).first()

        if not artefact:
            return Response(
                {"error": "No Consent artefact found with the given id"},
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

        # TODO: save entries in s3 bucket

        # TODO: call notify endpoint

        return Response(status=status.HTTP_202_ACCEPTED)
