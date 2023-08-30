from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.abdm.api.serializers.consent import ConsentSerializer
from care.abdm.models.consent import Consent
from care.abdm.service.gateway import Gateway
from care.utils.queryset.facility import get_facility_queryset
from config.authentication import ABDMAuthentication


class ConsentViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    serializer_class = ConsentSerializer
    model = Consent
    queryset = Consent.objects.all()
    permission_classes = (IsAuthenticated,)
    filterset_fields = ["status", "patient_health_id", "requester"]

    def get_queryset(self):
        queryset = self.queryset
        facilities = get_facility_queryset(self.request.user)
        return queryset.filter(requester__facility__in=facilities)

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        consent = Consent(**serializer.validated_data, requester=request.user)

        response = Gateway().consent_requests__init(consent)
        if response.status_code != 202:
            return Response(response.json(), status=response.status_code)

        consent.save()
        return Response(ConsentSerializer(consent).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["GET"])
    def status(self, request, pk):
        consent = self.queryset.filter(external_id=pk).first()

        if not consent:
            return Response(status=status.HTTP_404_NOT_FOUND)

        response = Gateway().consent_requests__status(str(consent.consent_id))
        if response.status_code != 202:
            return Response(response.json(), status=response.status_code)

        return Response(ConsentSerializer(consent).data, status=status.HTTP_200_OK)


class ConsentCallbackViewSet(GenericViewSet):
    permission_classes = (IsAuthenticated,)
    authentication_classes = [ABDMAuthentication]

    def consent_request__on_init(self, request):
        data = request.data
        consent = Consent.objects.filter(external_id=data["resp"]["requestId"]).first()

        if not consent:
            return Response(status=status.HTTP_404_NOT_FOUND)

        consent.consent_id = data["consentRequest"]["id"]
        consent.save()

        return Response(status=status.HTTP_202_ACCEPTED)

    def consent_request__on_status(self, request):
        data = request.data
        consent = Consent.objects.filter(
            consent_id=data["consentRequest"]["id"]
        ).first()

        if not consent:
            return Response(status=status.HTTP_404_NOT_FOUND)

        consent.status = data["consentRequest"]["status"]
        consent_artefacts = data["consentRequest"]["consentArtefacts"]
        consent.artefacts = consent_artefacts if consent_artefacts else []
        consent.save()

        return Response(status=status.HTTP_202_ACCEPTED)

    def consents__hiu__notify(self, request):
        data = request.data
        consent = Consent.objects.filter(
            consent_id=data["notification"]["consentRequestId"]
        ).first()

        if not consent:
            return Response(status=status.HTTP_404_NOT_FOUND)

        consent.status = data["notification"]["status"]
        consent.artefacts = data["notification"]["consentArtefacts"]
        consent.save()

        return Response(status=status.HTTP_202_ACCEPTED)
