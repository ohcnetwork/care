from rest_framework.serializers import CharField, Serializer


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


# {
#   "email": "Example@Demo.com",
#   "firstName": "manoj",
#   "healthId": "deepak.pant",
#   "lastName": "singh",
#   "middleName": "kishan",
#   "password": "India@143",
#   "profilePhoto": "/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkJCQkJCQoLCwoODw0PDhQSERESFB4WFxYXFh4uHSEdHSEdLikxKCUoMSlJOTMzOUlUR0NHVGZbW2aBeoGoqOIBCQkJCQkJCgsLCg4PDQ8OFBIRERIUHhYXFhcWHi4dIR0dIR0uKTEoJSgxKUk5MzM5SVRHQ0dUZltbZoF6gaio4v/CABEIBLAHgAMBIgACEQEDEQH/xAAbAAACAwEBAQAAAAAAAAAAAAACAwABBAUGB//aAAgBAQAAAADwawLpMspcK7qrlE5F0Vtul2bVywMUNeBHUkW/bmxvYELGuNjh2VDvixxo5ViljKjDRMoahCULjs2JCShjhjh2OGxo0Y2MoXHOLszsKLhw7tD99mpZQxj8xceofmLEKFwXLTIyHwY1Ls+iEotjHY0M0pjRYxtGj4VFKLPohQlFQyy4Qipc0XG9pS+CP/2Q==",
#   "txnId": "a825f76b-0696-40f3-864c-5a3a5b389a83"
# }
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
    patientId = CharField(required=True, help_text="Patient ID to be linked",
                          validators=[])  # TODO: Add UUID Validation
