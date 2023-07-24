from rest_framework.serializers import CharField, IntegerField, Serializer


class AddressSerializer(Serializer):
    line = CharField()
    district = CharField()
    state = CharField()
    pincode = CharField()


class PatientSerializer(Serializer):
    healthId = CharField(allow_null=True)
    healthIdNumber = CharField()
    name = CharField()
    gender = CharField()
    yearOfBirth = IntegerField()
    dayOfBirth = IntegerField()
    monthOfBirth = IntegerField()
    address = AddressSerializer()


class ProfileSerializer(Serializer):
    hipCode = CharField()
    patient = PatientSerializer()


class HipShareProfileSerializer(Serializer):
    """
    Serializer for the request of the share_profile
    """

    requestId = CharField()
    profile = ProfileSerializer()
