from rest_framework.serializers import CharField, Serializer, UUIDField


class AadharOtpGenerateRequestPayloadSerializer(Serializer):
    aadhaar = CharField(max_length=16, min_length=12, required=True)


class AadharOtpResendRequestPayloadSerializer(Serializer):
    txnId = CharField(max_length=64, min_length=1, required=True)


class HealthIdSerializer(Serializer):
    healthId = CharField(max_length=64, min_length=1, required=True)


class QRContentSerializer(Serializer):
    hidn = CharField(max_length=17, min_length=17, required=True)
    phr = CharField(max_length=64, min_length=1, required=True)
    name = CharField(max_length=64, min_length=1, required=True)
    gender = CharField(max_length=1, min_length=1, required=True)
    dob = CharField(max_length=10, min_length=8, required=True)


class HealthIdAuthSerializer(Serializer):
    authMethod = CharField(max_length=64, min_length=1, required=True)
    healthid = CharField(max_length=64, min_length=1, required=True)


class ABHASearchRequestSerializer:
    name = CharField(max_length=64, min_length=1, required=False)
    mobile = CharField(
        max_length=10,
        min_length=10,
        required=False,
    )
    gender = CharField(max_length=1, min_length=1, required=False)
    yearOfBirth = CharField(max_length=4, min_length=4, required=False)


class GenerateMobileOtpRequestPayloadSerializer(Serializer):
    mobile = CharField(max_length=10, min_length=10, required=True)
    txnId = CharField(max_length=64, min_length=1, required=True)


class VerifyOtpRequestPayloadSerializer(Serializer):
    otp = CharField(max_length=6, min_length=6, required=True, help_text="OTP")
    txnId = CharField(max_length=64, min_length=1, required=True)
    patientId = UUIDField(required=False)


class VerifyDemographicsRequestPayloadSerializer(Serializer):
    gender = CharField(max_length=10, min_length=1, required=True)
    name = CharField(max_length=64, min_length=1, required=True)
    yearOfBirth = CharField(max_length=4, min_length=4, required=True)
    txnId = CharField(max_length=64, min_length=1, required=True)


class CreateHealthIdSerializer(Serializer):
    healthId = CharField(max_length=64, min_length=1, required=False)
    txnId = CharField(max_length=64, min_length=1, required=True)
    patientId = UUIDField(required=False)
