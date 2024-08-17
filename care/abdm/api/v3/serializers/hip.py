from typing import Any

from rest_framework.exceptions import APIException
from rest_framework.serializers import (
    CharField,
    ChoiceField,
    DateTimeField,
    IntegerField,
    ListField,
    Serializer,
    URLField,
    UUIDField,
)

from care.abdm.models import (
    AccessMode,
    FrequencyUnit,
    HealthInformationTypes,
    Purpose,
    Status,
)
from care.utils.queryset.consultation import get_consultation_queryset


class LinkCarecontextSerializer(Serializer):
    consultations = ListField(child=UUIDField(), required=True)

    def validate(self, attrs: Any) -> Any:
        consultation_instances = get_consultation_queryset(
            self.context["request"].user
        ).filter(external_id__in=attrs["consultations"])

        if consultation_instances.count() != len(attrs["consultations"]):
            raise APIException(
                detail="You do not have access to one or more consultations"
            )

        attrs["consultations"] = consultation_instances
        return super().validate(attrs)


class TokenOnGenerateTokenSerializer(Serializer):
    class ResponseSerializer(Serializer):
        requestId = UUIDField(required=True)

    abhaAddress = CharField(max_length=50, required=True)
    linkToken = CharField(max_length=1000, required=True)
    response = ResponseSerializer(required=True)


class LinkOnCarecontextSerializer(Serializer):

    class ErrorSerializer(Serializer):
        code = CharField(max_length=50, required=True)
        message = CharField(max_length=1000, required=True)

    class ResponseSerializer(Serializer):
        requestId = UUIDField(required=True)

    abhaAddress = CharField(max_length=50, required=True)
    status = CharField(max_length=1000, required=False)
    error = ErrorSerializer(required=False)
    response = ResponseSerializer(required=True)


class HipPatientCareContextDiscoverSerializer(Serializer):
    class PatientSerializer(Serializer):
        class IdentifierSerializer(Serializer):
            type = ChoiceField(
                choices=["MOBILE", "ABHA_NUMBER", "MR", "abhaAddress"], required=True
            )
            value = CharField(max_length=255, required=True)

        id = CharField(max_length=50, required=True)
        name = CharField(max_length=100, required=True)
        gender = ChoiceField(choices=["M", "F", "O"], required=True)
        yearOfBirth = IntegerField(required=True)
        verifiedIdentifiers = IdentifierSerializer(many=True, required=True)
        unverifiedIdentifiers = IdentifierSerializer(many=True, required=True)

    transactionId = UUIDField(required=True)
    patient = PatientSerializer(required=True)


class HipLinkCareContextInitSerializer(Serializer):
    class PatientSerializer(Serializer):
        class CareContextSerializer(Serializer):
            referenceNumber = CharField(max_length=50, required=True)

        referenceNumber = CharField(max_length=50, required=True)
        careContexts = CareContextSerializer(many=True, required=True)
        hiType = ChoiceField(
            choices=HealthInformationTypes.choices,
            required=True,
        )
        count = IntegerField(required=True)

    transactionId = UUIDField(required=True)
    abhaAddress = CharField(max_length=50, required=True)
    patient = PatientSerializer(many=True, required=True)


class HipLinkCareContextConfirmSerializer(Serializer):
    class ConfirmationSerializer(Serializer):
        linkRefNumber = CharField(max_length=50, required=True)
        token = CharField(max_length=20, required=True)

    confirmation = ConfirmationSerializer(required=True)


class HipConsentRequestNotifySerializer(Serializer):
    class NotificationSerializer(Serializer):
        class ConsentDetailSerializer(Serializer):
            class PatientSerializer(Serializer):
                id = CharField(max_length=50, required=True)

            class CareContextSerializer(Serializer):
                patientReference = CharField(max_length=50, required=True)
                careContextReference = CharField(max_length=50, required=True)

            class PurposeSerializer(Serializer):
                text = CharField(max_length=50, required=False)
                code = ChoiceField(choices=Purpose.choices, required=True)
                refUri = CharField(max_length=50, allow_null=True)

            class HipSerializer(Serializer):
                id = CharField(max_length=50, required=True)
                name = CharField(max_length=50, required=True)

            class ConsentManagerSerializer(Serializer):
                id = CharField(max_length=50, required=True)

            class PermissionSerializer(Serializer):
                class DataRangeSerializer(Serializer):
                    fromTime = DateTimeField(source="from", required=True)
                    toTime = DateTimeField(source="to", required=True)

                class FrequencySerializer(Serializer):
                    unit = ChoiceField(choices=FrequencyUnit.choices, required=True)
                    value = IntegerField(required=True)
                    repeats = IntegerField(required=True)

                accessMode = ChoiceField(choices=AccessMode.choices, required=True)
                dateRange = DataRangeSerializer(required=True)
                frequency = FrequencySerializer(required=True)

            schemaVersion = CharField(max_length=50, required=True)
            consentId = UUIDField(required=True)
            createdAt = DateTimeField(required=True)
            patient = PatientSerializer(required=True)
            careContexts = CareContextSerializer(many=True, required=True)
            purpose = PurposeSerializer(required=True)
            hip = HipSerializer(required=True)
            consentManager = ConsentManagerSerializer(required=True)
            hiTypes = ListField(
                child=ChoiceField(choices=HealthInformationTypes.choices),
                required=True,
            )
            permission = PermissionSerializer(required=True)

        status = ChoiceField(choices=Status.choices, required=True)
        consentId = UUIDField(required=True)
        consentDetail = ConsentDetailSerializer(required=True)
        signature = CharField(max_length=500, required=True)

    notification = NotificationSerializer(required=True)


class HealthInformationHipRequestSerializer(Serializer):
    class HiRequestSerializer(Serializer):
        class ConsentSerializer(Serializer):
            id = UUIDField(required=True)

        class DateRangeSerializer(Serializer):
            fromTime = DateTimeField(source="from", required=True)
            toTime = DateTimeField(source="to", required=True)

        class KeyMaterialSerializer(Serializer):
            class DhPublicKeySerializer(Serializer):
                expiry = DateTimeField(required=True)
                parameters = CharField(max_length=50, required=False)
                keyValue = CharField(max_length=500, required=True)

            cryptoAlg = CharField(max_length=50, required=True)
            curve = CharField(max_length=50, required=True)
            dhPublicKey = DhPublicKeySerializer(required=True)
            nonce = CharField(max_length=50, required=True)

        consent = ConsentSerializer(required=True)
        dateRange = DateRangeSerializer(required=True)
        dataPushUrl = URLField(required=True)
        keyMaterial = KeyMaterialSerializer(required=True)

    transactionId = UUIDField(required=True)
    hiRequest = HiRequestSerializer(required=True)
