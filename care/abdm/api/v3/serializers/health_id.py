from rest_framework.serializers import CharField, Serializer, UUIDField


class SendAadhaarOtpSerializer(Serializer):
    aadhaar = CharField(max_length=12, min_length=12, required=True)


class VerifyAadhaarOtpSerializer(Serializer):
    transaction_id = UUIDField(required=True)
    otp = CharField(max_length=6, min_length=6, required=True)
    mobile = CharField(max_length=10, min_length=10, required=True)


class LinkMobileNumberSerializer(Serializer):
    mobile = CharField(max_length=10, min_length=10, required=True)
    transaction_id = UUIDField(required=True)


class VerifyMobileOtpSerializer(Serializer):
    transaction_id = UUIDField(required=True)
    otp = CharField(max_length=6, min_length=6, required=True)


class AbhaAddressSuggestionSerializer(Serializer):
    transaction_id = UUIDField(required=True)


class EnrolAbhaAddressSerializer(Serializer):
    transaction_id = UUIDField(required=True)
    abha_address = CharField(min_length=3, max_length=14, required=True)
