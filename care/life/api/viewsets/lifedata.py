from django.db.models import F
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from care.life.api.serializers.lifedata import LifeDataSerializer
from care.life.models import LifeData

from config.ratelimit import validatecaptcha
from config.auth_views import CaptchaRequiredException


class LifeDataViewSet(GenericViewSet):
    queryset = LifeData.objects.all()
    serializer_class = LifeDataSerializer
    permission_classes = []
    authentication_classes = []
    lookup_field = "external_id"

    @swagger_auto_schema(method="post", request_body=serializers.Serializer(), responses={204: "Success"})
    @action(detail=True, methods=["POST"])
    def downvote(self, request, *args, **kwargs):
        if not validatecaptcha(request):
            raise CaptchaRequiredException
        external_id = kwargs["external_id"]
        try:
            LifeData.objects.filter(external_id=external_id).update(downvotes=F("downvotes") + 1)
        except:
            pass

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(method="post", request_body=serializers.Serializer(), responses={204: "Success"})
    @action(detail=True, methods=["POST"])
    def upvote(self, request, *args, **kwargs):
        if not validatecaptcha(request):
            raise CaptchaRequiredException
        external_id = kwargs["external_id"]
        try:
            LifeData.objects.filter(external_id=external_id).update(upvotes=F("upvotes") + 1)
        except:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)
