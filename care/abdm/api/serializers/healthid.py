from rest_framework.serializers import CharField, Serializer, UUIDField


class AadharOtpGenerateRequestPayloadSerializer(Serializer):
    aadhaar = CharField(
        max_length=16,
        min_length=12,
        required=True,
        help_text="Aadhaar Number",
        validators=[],
    )


class AadharOtpResendRequestPayloadSerializer(Serializer):
    txnId = CharField(
        max_length=64,
        min_length=1,
        required=True,
        help_text="Transaction ID",
        validators=[],
    )


class HealthIdSerializer(Serializer):
    healthId = CharField(
        max_length=64,
        min_length=1,
        required=True,
        help_text="Health ID",
    )


class QRContentSerializer(Serializer):
    hidn = CharField(
        max_length=17,
        min_length=17,
        required=True,
        help_text="Health ID Number",
    )
    phr = CharField(
        max_length=64,
        min_length=1,
        required=True,
        help_text="Health ID",
    )
    name = CharField(
        max_length=64,
        min_length=1,
        required=True,
        help_text="Name",
    )
    gender = CharField(
        max_length=1,
        min_length=1,
        required=True,
        help_text="Name",
    )
    dob = CharField(
        max_length=10,
        min_length=8,
        required=True,
        help_text="Name",
    )


class HealthIdAuthSerializer(Serializer):
    authMethod = CharField(
        max_length=64,
        min_length=1,
        required=True,
        help_text="Auth Method",
    )
    healthid = CharField(
        max_length=64,
        min_length=1,
        required=True,
        help_text="Health ID",
    )


class ABHASearchRequestSerializer:
    name = CharField(max_length=64, min_length=1, required=False, help_text="Name")
    mobile = CharField(
        max_length=10, min_length=10, required=False, help_text="Mobile Number"
    )
    gender = CharField(max_length=1, min_length=1, required=False, help_text="Gender")
    yearOfBirth = CharField(
        max_length=4, min_length=4, required=False, help_text="Year of Birth"
    )


class GenerateMobileOtpRequestPayloadSerializer(Serializer):
    mobile = CharField(
        max_length=10,
        min_length=10,
        required=True,
        help_text="Mobile Number",
        validators=[],
    )
    txnId = CharField(
        max_length=64,
        min_length=1,
        required=True,
        help_text="Transaction ID",
        validators=[],
    )


class VerifyOtpRequestPayloadSerializer(Serializer):
    otp = CharField(
        max_length=6,
        min_length=6,
        required=True,
        help_text="OTP",
        validators=[],
    )
    txnId = CharField(
        max_length=64,
        min_length=1,
        required=True,
        help_text="Transaction ID",
        validators=[],
    )
    patientId = UUIDField(
        required=False, help_text="Patient ID to be linked", validators=[]
    )


class VerifyDemographicsRequestPayloadSerializer(Serializer):
    gender = CharField(
        max_length=10,
        min_length=1,
        required=True,
        help_text="Gender",
        validators=[],
    )
    name = CharField(
        max_length=64,
        min_length=1,
        required=True,
        help_text="Name",
        validators=[],
    )
    yearOfBirth = CharField(
        max_length=4,
        min_length=4,
        required=True,
        help_text="Year Of Birth",
        validators=[],
    )
    txnId = CharField(
        max_length=64,
        min_length=1,
        required=True,
        help_text="Transaction ID",
        validators=[],
    )


class CreateHealthIdSerializer(Serializer):
    healthId = CharField(
        max_length=64,
        min_length=1,
        required=False,
        help_text="Health ID",
        validators=[],
    )
    txnId = CharField(
        max_length=64,
        min_length=1,
        required=True,
        help_text="PreVerified Transaction ID",
        validators=[],
    )
    patientId = UUIDField(
        required=False, help_text="Patient ID to be linked", validators=[]
    )
