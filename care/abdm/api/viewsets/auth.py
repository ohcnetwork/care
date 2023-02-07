from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from care.abdm.utils.api_call import AbdmGateway


class OnFetchView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        data = request.data
        print("on-fetch-modes", data)
        AbdmGateway().init(data["resp"]["requestId"])
        return Response({}, status=status.HTTP_202_ACCEPTED)


class OnInitView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        data = request.data
        print("on-init", data)
        AbdmGateway().confirm(data["auth"]["transactionId"], data["resp"]["requestId"])
        return Response({}, status=status.HTTP_202_ACCEPTED)


class OnConfirmView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        data = request.data
        print(data)
        AbdmGateway().link_patient_abha(
            data["auth"]["patient"],
            data["auth"]["accessToken"],
            data["resp"]["requestId"],
        )
        return Response({}, status=status.HTTP_202_ACCEPTED)
