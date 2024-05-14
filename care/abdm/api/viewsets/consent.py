import logging

from django_filters import rest_framework as filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.abdm.api.serializers.consent import ConsentRequestSerializer
from care.abdm.api.viewsets.health_information import HealthInformationViewSet
from care.abdm.models.base import Status
from care.abdm.models.consent import ConsentArtefact, ConsentRequest
from care.abdm.service.gateway import Gateway
from care.utils.queryset.facility import get_facility_queryset
from config.auth_views import CaptchaRequiredException
from config.authentication import ABDMAuthentication
from config.ratelimit import ratelimit

logger = logging.getLogger(__name__)


class ConsentRequestFilter(filters.FilterSet):
    patient = filters.UUIDFilter(
        field_name="patient_abha__patientregistration__external_id"
    )
    health_id = filters.CharFilter(field_name="patient_abha__health_id")
    ordering = filters.OrderingFilter(
        fields=(
            "created_date",
            "updated_date",
        )
    )
    facility = filters.UUIDFilter(
        field_name="patient_abha__patientregistration__facility__external_id"
    )

    class Meta:
        model = ConsentRequest
        fields = ["patient", "health_id", "purpose"]


class ConsentViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    serializer_class = ConsentRequestSerializer
    model = ConsentRequest
    queryset = ConsentRequest.objects.all()
    permission_classes = (IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ConsentRequestFilter

    def get_queryset(self):
        queryset = self.queryset
        facilities = get_facility_queryset(self.request.user)
        return queryset.filter(requester__facility__in=facilities).distinct()

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if ratelimit(
            request, "consent__create", [serializer.validated_data["patient_abha"]]
        ):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        consent = ConsentRequest(**serializer.validated_data, requester=request.user)

        try:
            response = Gateway().consent_requests__init(consent)
            if response.status_code != 202:
                return Response(response.json(), status=response.status_code)
        except Exception as e:
            logger.warning(
                f"Error: ConsentViewSet::create failed to notify (consent_requests__init). Reason: {e}",
                exc_info=True,
            )
            return Response(
                {"detail": "Failed to initialize consent request"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        consent.save()
        return Response(
            ConsentRequestSerializer(consent).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["GET"])
    def status(self, request, pk):
        if ratelimit(request, "consent__status", [pk]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        consent = self.queryset.filter(external_id=pk).first()

        if not consent:
            return Response(status=status.HTTP_404_NOT_FOUND)

        response = Gateway().consent_requests__status(str(consent.consent_id))
        if response.status_code != 202:
            return Response(response.json(), status=response.status_code)

        return Response(
            ConsentRequestSerializer(consent).data, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["GET"])
    def fetch(self, request, pk):
        if ratelimit(request, "consent__fetch", [pk]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        consent = self.queryset.filter(external_id=pk).first()

        if not consent:
            return Response(status=status.HTTP_404_NOT_FOUND)

        for artefact in consent.consent_artefacts.all():
            response = Gateway().consents__fetch(str(artefact.artefact_id))

            if response.status_code != 202:
                return Response(response.json(), status=response.status_code)

        return Response(
            ConsentRequestSerializer(consent).data, status=status.HTTP_200_OK
        )

    def list(self, request, *args, **kwargs):
        if ratelimit(request, "consent__list", [request.user.username]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if ratelimit(request, "consent__retrieve", [kwargs["pk"]]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        return super().retrieve(request, *args, **kwargs)


class ConsentCallbackViewSet(GenericViewSet):
    permission_classes = (IsAuthenticated,)
    authentication_classes = [ABDMAuthentication]

    def consent_request__on_init(self, request):
        data = request.data
        consent = ConsentRequest.objects.filter(
            external_id=data["resp"]["requestId"]
        ).first()

        if not consent:
            return Response(status=status.HTTP_404_NOT_FOUND)

        consent.consent_id = data["consentRequest"]["id"]
        consent.save()

        return Response(status=status.HTTP_202_ACCEPTED)

    def consent_request__on_status(self, request):
        data = request.data
        consent = ConsentRequest.objects.filter(
            consent_id=data["consentRequest"]["id"]
        ).first()

        if not consent:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if "notification" not in data:
            return Response(status=status.HTTP_202_ACCEPTED)

        if data["notification"]["status"] != Status.DENIED:
            consent_artefacts = data["notification"]["consentArtefacts"] or []
            for artefact in consent_artefacts:
                consent_artefact = ConsentArtefact.objects.filter(
                    external_id=artefact["id"]
                ).first()
                if not consent_artefact:
                    consent_artefact = ConsentArtefact(
                        external_id=artefact["id"],
                        consent_request=consent,
                        **consent.consent_details_dict(),
                    )

                consent_artefact.status = data["notification"]["status"]
                consent_artefact.save()
        consent.status = data["notification"]["status"]
        consent.save()

        return Response(status=status.HTTP_202_ACCEPTED)

    def consents__hiu__notify(self, request):
        data = request.data

        if not data["notification"]["consentRequestId"]:
            for artefact in data["notification"]["consentArtefacts"]:
                consent_artefact = ConsentArtefact.objects.filter(
                    external_id=artefact["id"]
                ).first()

                consent_artefact.status = Status.REVOKED
                consent_artefact.save()
            return Response(status=status.HTTP_202_ACCEPTED)

        consent = ConsentRequest.objects.filter(
            consent_id=data["notification"]["consentRequestId"]
        ).first()

        if not consent:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if data["notification"]["status"] != Status.DENIED:
            consent_artefacts = data["notification"]["consentArtefacts"] or []
            for artefact in consent_artefacts:
                consent_artefact = ConsentArtefact.objects.filter(
                    external_id=artefact["id"]
                ).first()
                if not consent_artefact:
                    consent_artefact = ConsentArtefact(
                        external_id=artefact["id"],
                        consent_request=consent,
                        **consent.consent_details_dict(),
                    )

                consent_artefact.status = data["notification"]["status"]
                consent_artefact.save()
        consent.status = data["notification"]["status"]
        consent.save()

        Gateway().consents__hiu__on_notify(consent, data["requestId"])

        if data["notification"]["status"] == Status.GRANTED:
            ConsentViewSet().fetch(request, consent.external_id)

        return Response(status=status.HTTP_202_ACCEPTED)

    def consents__on_fetch(self, request):
        data = request.data["consent"]
        artefact = ConsentArtefact.objects.filter(
            external_id=data["consentDetail"]["consentId"]
        ).first()

        if not artefact:
            return Response(status=status.HTTP_404_NOT_FOUND)

        artefact.hip = data["consentDetail"]["hip"]["id"]
        artefact.hiu = data["consentDetail"]["hiu"]["id"]
        artefact.cm = data["consentDetail"]["consentManager"]["id"]

        artefact.care_contexts = data["consentDetail"]["careContexts"]
        artefact.hi_types = data["consentDetail"]["hiTypes"]

        artefact.access_mode = data["consentDetail"]["permission"]["accessMode"]
        artefact.from_time = data["consentDetail"]["permission"]["dateRange"]["from"]
        artefact.to_time = data["consentDetail"]["permission"]["dateRange"]["to"]
        artefact.expiry = data["consentDetail"]["permission"]["dataEraseAt"]

        artefact.frequency_unit = data["consentDetail"]["permission"]["frequency"][
            "unit"
        ]
        artefact.frequency_value = data["consentDetail"]["permission"]["frequency"][
            "value"
        ]
        artefact.frequency_repeats = data["consentDetail"]["permission"]["frequency"][
            "repeats"
        ]

        artefact.signature = data["signature"]
        artefact.save()

        HealthInformationViewSet().request(request, artefact.external_id)

        return Response(status=status.HTTP_202_ACCEPTED)
