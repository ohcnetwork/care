from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.abdm.models.abha_number import AbhaNumber
from care.abdm.service.gateway import Gateway
from config.authentication import ABDMAuthentication


class PatientsViewSet(GenericViewSet):
    permission_classes = (IsAuthenticated,)

    @action(detail=False, methods=["POST"])
    def find(self, request):
        identifier = request.data["id"]
        abha_object = AbhaNumber.objects.filter(
            Q(abha_number=identifier) | Q(health_id=identifier)
        ).first()

        if not abha_object:
            return Response(
                {"error": "Patient with given id not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        response = Gateway().patients__find(abha_object)
        if response.status_code != 202:
            return Response(response.json(), status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_200_OK)


class PatientsCallbackViewSet(GenericViewSet):
    permission_classes = (IsAuthenticated,)
    authentication_classes = [ABDMAuthentication]

    def patients__on_find(self, request):
        # TODO: send a push notification
        return Response(status=status.HTTP_202_ACCEPTED)
