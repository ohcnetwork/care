import base64
from typing import List

from django.conf import settings
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.notification import NotificationSerializer
from care.facility.models.notification import Notification


class NotificationViewSet(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = Notification.objects.all().select_related("intended_for", "caused_by").order_by("-created_date")
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "external_id"

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(intended_for=user)

    @action(detail=False, methods=["GET"], permission_classes=[IsAuthenticatedOrReadOnly])
    def public_key(self, request, *args, **kwargs):
        return Response({"public_key": base64.urlsafe_b64encode(str.encode(settings.VAPID_PUBLIC_KEY))})
