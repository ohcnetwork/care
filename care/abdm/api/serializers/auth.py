from rest_framework.serializers import CharField, IntegerField, Serializer


class AbdmAuthResponseSerializer(Serializer):
    """
    Serializer for the response of the authentication API
    """

    accessToken = CharField()
    refreshToken = CharField()
    expiresIn = IntegerField()
    refreshExpiresIn = IntegerField()
    tokenType = CharField()


class AbdmAuthInitResponseSerializer(Serializer):
    """
    Serializer for the response of the authentication API
    """

    token = CharField()
    refreshToken = CharField()
    expiresIn = IntegerField()
    refreshExpiresIn = IntegerField()
