from rest_framework.serializers import CharField, ChoiceField, Serializer, UUIDField


class AbhaCreateSendAadhaarOtpSerializer(Serializer):
    aadhaar = CharField(max_length=12, min_length=12, required=True)


class AbhaCreateVerifyAadhaarOtpSerializer(Serializer):
    transaction_id = UUIDField(required=True)
    otp = CharField(max_length=6, min_length=6, required=True)
    mobile = CharField(max_length=10, min_length=10, required=True)


class AbhaCreateLinkMobileNumberSerializer(Serializer):
    mobile = CharField(max_length=10, min_length=10, required=True)
    transaction_id = UUIDField(required=True)


class AbhaCreateVerifyMobileOtpSerializer(Serializer):
    transaction_id = UUIDField(required=True)
    otp = CharField(max_length=6, min_length=6, required=True)


class AbhaCreateAbhaAddressSuggestionSerializer(Serializer):
    transaction_id = UUIDField(required=True)


class AbhaCreateEnrolAbhaAddressSerializer(Serializer):
    transaction_id = UUIDField(required=True)
    abha_address = CharField(min_length=3, max_length=50, required=True)


class AbhaLoginSendOtpSerializer(Serializer):
    TYPE_CHOICES = [
        ("aadhaar", "Aadhaar"),
        ("mobile", "Mobile"),
        ("abha-number", "ABHA Number"),
        ("abha-address", "ABHA Address"),
    ]

    OTP_SYSTEM_CHOICES = [
        ("aadhaar", "Aadhaar"),
        ("abdm", "Abdm"),
    ]

    type = ChoiceField(choices=TYPE_CHOICES, required=True)
    value = CharField(max_length=50, required=True)
    otp_system = ChoiceField(choices=OTP_SYSTEM_CHOICES, required=True)


class AbhaLoginVerifyOtpSerializer(Serializer):
    TYPE_CHOICES = [
        ("aadhaar", "Aadhaar"),
        ("mobile", "Mobile"),
        ("abha-number", "ABHA Number"),
        ("abha-address", "ABHA Address"),
    ]

    OTP_SYSTEM_CHOICES = [
        ("aadhaar", "Aadhaar"),
        ("abdm", "Abdm"),
    ]

    type = ChoiceField(choices=TYPE_CHOICES, required=True)
    otp = CharField(max_length=6, min_length=6, required=True)
    otp_system = ChoiceField(choices=OTP_SYSTEM_CHOICES, required=True)
    transaction_id = UUIDField(required=True)


class AbhaLoginCheckAuthMethodsSerializer(Serializer):
    abha_address = CharField(max_length=50, min_length=3, required=True)


class LinkAbhaNumberAndPatientSerializer(Serializer):
    patient = UUIDField(required=True)
    abha_number = UUIDField(required=True)
