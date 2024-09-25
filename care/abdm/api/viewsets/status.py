from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from care.abdm.models import AbhaNumber
from care.abdm.utils.api_call import AbdmGateway
from care.facility.models.patient import PatientRegistration
from config.authentication import ABDMAuthentication


class NotifyView(GenericAPIView):
    authentication_classes = [ABDMAuthentication]

    def post(self, request, *args, **kwargs):
        data = request.data

        PatientRegistration.objects.filter(
            abha_number__health_id=data["notification"]["patient"]["id"]
        ).update(abha_number=None)
        AbhaNumber.objects.filter(
            health_id=data["notification"]["patient"]["id"]
        ).delete()

        AbdmGateway().patient_status_on_notify({"request_id": data["requestId"]})

        return Response(status=status.HTTP_202_ACCEPTED)


class SMSOnNotifyView(GenericAPIView):
    authentication_classes = [ABDMAuthentication]

    def post(self, request, *args, **kwargs):
        return Response(status=status.HTTP_202_ACCEPTED)
