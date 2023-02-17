from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from care.hcx.utils.hcx import Hcx
from care.utils.notification_handler import send_webpush
import json


class CoverageElibilityOnCheckView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    @swagger_auto_schema(tags=["hcx"])
    def post(self, request, *args, **kwargs):
        data = Hcx().processIncomingRequest(request.data["payload"])

        message = {
            "type": "MESSAGE",
            "from": "coverageelegibility/on_check",
            "data": data,
        }
        send_webpush(username="devdistrictadmin", message=json.dumps(message))

        return Response({}, status=status.HTTP_202_ACCEPTED)


class PreAuthOnSubmitView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    @swagger_auto_schema(tags=["hcx"])
    def post(self, request, *args, **kwargs):
        data = Hcx().processIncomingRequest(request.data["payload"])

        print("--------------------------------------")
        print("pre auth on submit", data)
        print("--------------------------------------")
        return Response({}, status=status.HTTP_202_ACCEPTED)


class ClaimOnSubmitView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    @swagger_auto_schema(tags=["hcx"])
    def post(self, request, *args, **kwargs):
        data = Hcx().processIncomingRequest(request.data["payload"])

        print("--------------------------------------")
        print("claim on submit", data)
        print("--------------------------------------")
        return Response({}, status=status.HTTP_202_ACCEPTED)
